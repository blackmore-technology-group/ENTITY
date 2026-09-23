from __future__ import annotations

from pathlib import Path
import hashlib
import json
import re
import sqlite3
import time

PROFILE = "ENTITY_MARKET_STATE_RECOVERY"
VERSION = "3.0.0"
SCHEMA = "entity-v3-market-recovery-bundle-v1"

EEP_REQUIRED = (
    "venues", "instruments", "balances", "listings", "orders", "trades",
    "clearing", "entitlements", "disclosures", "usage", "revenue_rules",
    "revenue_rule_sets", "trade_revenue_bindings", "surveillance", "rfqs", "quotes", "rfq_acceptances",
    "order_cancellations", "settlement_verifiers", "payment_attestations",
)
EEP_OPTIONAL = ("revenue_events",)
EOPP_REQUIRED = (
    "treasuries", "participation_policies", "reserve_allocations",
    "economic_events", "obligations", "position_snapshots", "settlement_verifiers",
)
ENTITY_ID_RE = re.compile(r"^ent\d+-[a-z0-9]+$", re.IGNORECASE)


def canonical_bytes(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def semantic_sha256(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _decode_value(column: str, value):
    if value is None:
        return None
    if column.endswith("_json") and isinstance(value, str):
        return json.loads(value)
    return value


def _encode_value(column: str, value):
    if value is None:
        return None
    if column.endswith("_json"):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return value


def _quoted(identifier: str) -> str:
    if not identifier or '"' in identifier:
        raise ValueError("invalid SQLite identifier")
    return f'"{identifier}"'


def _table_names(db: sqlite3.Connection) -> set[str]:
    return {
        str(row[0]) for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    }


def _snapshot_table(db: sqlite3.Connection, table: str) -> dict:
    info = db.execute(f"PRAGMA table_info({_quoted(table)})").fetchall()
    if not info:
        raise KeyError(f"table missing: {table}")
    columns = [str(row[1]) for row in info]
    json_columns = sorted(c for c in columns if c.endswith("_json"))
    rows = []
    for raw in db.execute(f"SELECT * FROM {_quoted(table)}").fetchall():
        row = {columns[i]: _decode_value(columns[i], raw[i]) for i in range(len(columns))}
        rows.append(row)
    rows.sort(key=canonical_bytes)
    payload = {"columns": columns, "json_columns": json_columns, "rows": rows}
    return {
        **payload,
        "row_count": len(rows),
        "semantic_sha256": semantic_sha256(payload),
    }


def _snapshot_database(path: Path, required: tuple[str, ...], optional=()) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    db = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        db.execute("BEGIN")
        names = _table_names(db)
        missing = sorted(set(required) - names)
        if missing:
            raise ValueError(f"required tables missing: {missing}")
        selected = list(required) + sorted(set(optional) & names)
        tables = {name: _snapshot_table(db, name) for name in selected}
        state = {"tables": tables}
        return {
            "tables": tables,
            "table_count": len(tables),
            "row_count": sum(t["row_count"] for t in tables.values()),
            "state_sha256": semantic_sha256(state),
        }
    finally:
        db.close()


def _collect_signer_ids(value, out: set[str]) -> None:
    if isinstance(value, dict):
        schema = value.get("signature_schema")
        entity_id = value.get("entity_id")
        if isinstance(schema, str) and schema.startswith("entity-signature-record-") and isinstance(entity_id, str):
            out.add(entity_id)
        for item in value.values():
            _collect_signer_ids(item, out)
    elif isinstance(value, list):
        for item in value:
            _collect_signer_ids(item, out)


def _referenced_manifests(identity, *sections: dict) -> list[dict]:
    signer_ids: set[str] = set()
    for section in sections:
        _collect_signer_ids(section, signer_ids)
    manifests = []
    for entity_id in sorted(signer_ids):
        try:
            manifests.append(identity.load_manifest(entity_id))
        except Exception as exc:
            raise ValueError(f"signer ENTITY manifest unavailable: {entity_id}") from exc
    return manifests

def _table_payload(snapshot: dict) -> dict:
    return {
        "columns": snapshot["columns"],
        "json_columns": snapshot["json_columns"],
        "rows": snapshot["rows"],
    }


class MarketStateRecovery:
    """Portable logical-state recovery for EEP + EOPP market infrastructure."""

    @staticmethod
    def export(exchange_path, economic_path, identity, *, core_bundles=None) -> dict:
        exchange = _snapshot_database(Path(exchange_path), EEP_REQUIRED, EEP_OPTIONAL)
        economic = _snapshot_database(Path(economic_path), EOPP_REQUIRED)
        controllers = sorted({
            str(row["operator"])
            for row in exchange["tables"]["venues"]["rows"]
        } | {
            str(row["owner_entity_id"])
            for row in economic["tables"]["treasuries"]["rows"]
        })
        manifests = _referenced_manifests(identity, exchange, economic)
        manifest_ids = {str(m.get("entity_id")) for m in manifests}
        for controller in controllers:
            if controller not in manifest_ids:
                manifests.append(identity.load_manifest(controller))
        manifests.sort(key=lambda m: str(m.get("entity_id")))
        exported_at = int(time.time() * 1000)
        bundle = {
            "schema": SCHEMA,
            "profile": PROFILE,
            "protocol_version": VERSION,
            "exchange": exchange,
            "economic_participation": economic,
            "identity_manifests": manifests,
            "underlying_core_bundles": list(core_bundles or []),
            "required_controller_attestations": controllers,
            "provider_independent": True,
            "database_bytes_are_not_authority": True,
            "restore_requires_empty_destination": True,
            "exported_at_ms": exported_at,
        }
        semantic = {k: v for k, v in bundle.items() if k != "exported_at_ms"}
        bundle["semantic_sha256"] = semantic_sha256(semantic)
        attestations = []
        for controller in controllers:
            body = {
                "schema": "entity-v3-market-recovery-attestation-v1",
                "profile": PROFILE,
                "semantic_sha256": bundle["semantic_sha256"],
                "controller_entity_id": controller,
                "created_at_ms": exported_at,
                "attestation_is_authorization_not_legal_title": True,
            }
            attestations.append(dict(body, signature=identity.sign(controller, body)))
        bundle["bundle_attestations"] = attestations
        return bundle

    @staticmethod
    def verify(bundle: dict, *, verify_manifest=None, verify_signature=None,
               verify_core_bundle=None) -> dict:
        failures: list[str] = []
        b = dict(bundle or {})
        if b.get("schema") != SCHEMA:
            failures.append("schema_invalid")
        if b.get("protocol_version") != VERSION:
            failures.append("protocol_version_invalid")
        if b.get("provider_independent") is not True:
            failures.append("provider_independent_flag_missing")
        if b.get("database_bytes_are_not_authority") is not True:
            failures.append("database_authority_boundary_missing")
        for section_name, required in (("exchange", EEP_REQUIRED), ("economic_participation", EOPP_REQUIRED)):
            section = b.get(section_name) or {}
            tables = section.get("tables") or {}
            missing = sorted(set(required) - set(tables))
            if missing:
                failures.append(f"{section_name}_tables_missing:{','.join(missing)}")
            for table_name, snapshot in tables.items():
                payload = _table_payload(snapshot)
                if semantic_sha256(payload) != snapshot.get("semantic_sha256"):
                    failures.append(f"table_hash_invalid:{section_name}:{table_name}")
                if len(snapshot.get("rows") or []) != snapshot.get("row_count"):
                    failures.append(f"row_count_invalid:{section_name}:{table_name}")
            if semantic_sha256({"tables": tables}) != section.get("state_sha256"):
                failures.append(f"state_hash_invalid:{section_name}")
            expected_rows = sum(int(x.get("row_count") or 0) for x in tables.values())
            if expected_rows != section.get("row_count"):
                failures.append(f"database_row_count_invalid:{section_name}")

        manifests = {}
        for manifest in b.get("identity_manifests") or []:
            entity_id = str(manifest.get("entity_id") or "")
            if not entity_id or entity_id in manifests:
                failures.append(f"manifest_duplicate_or_invalid:{entity_id}")
                continue
            if verify_manifest is None:
                failures.append("manifest_verifier_required")
            elif not verify_manifest(manifest):
                failures.append(f"manifest_invalid:{entity_id}")
            manifests[entity_id] = manifest

        for core in b.get("underlying_core_bundles") or []:
            core_semantic = {k: v for k, v in core.items() if k not in {"exported_at_ms", "semantic_sha256"}}
            if semantic_sha256(core_semantic) != core.get("semantic_sha256"):
                failures.append(f"core_bundle_hash_invalid:{core.get('root_object_id')}")
            if verify_core_bundle is not None:
                result = verify_core_bundle(core)
                if not result.get("valid"):
                    failures.append(f"core_bundle_invalid:{core.get('root_object_id')}")

        semantic = {k: v for k, v in b.items() if k not in {"exported_at_ms", "semantic_sha256", "bundle_attestations"}}
        actual_semantic = semantic_sha256(semantic)
        if actual_semantic != b.get("semantic_sha256"):
            failures.append("bundle_semantic_hash_invalid")

        required_controllers = set(b.get("required_controller_attestations") or [])
        attested = set()
        for attestation in b.get("bundle_attestations") or []:
            signature = attestation.get("signature")
            body = {k: v for k, v in attestation.items() if k != "signature"}
            controller = str(body.get("controller_entity_id") or "")
            if controller in attested:
                failures.append(f"controller_attestation_duplicate:{controller}")
                continue
            if controller not in required_controllers:
                failures.append(f"controller_attestation_unexpected:{controller}")
            if body.get("schema") != "entity-v3-market-recovery-attestation-v1" or body.get("profile") != PROFILE:
                failures.append(f"controller_attestation_shape_invalid:{controller}")
            if body.get("semantic_sha256") != b.get("semantic_sha256"):
                failures.append(f"controller_attestation_root_invalid:{controller}")
            manifest = manifests.get(controller)
            if verify_signature is None:
                failures.append("controller_attestation_verifier_required")
            elif manifest is None or not verify_signature(manifest, body, signature or {}):
                failures.append(f"controller_attestation_signature_invalid:{controller}")
            attested.add(controller)
        for controller in sorted(required_controllers - attested):
            failures.append(f"controller_attestation_missing:{controller}")

        return {
            "valid": not failures,
            "failures": failures,
            "semantic_sha256": b.get("semantic_sha256"),
            "exchange_state_sha256": (b.get("exchange") or {}).get("state_sha256"),
            "economic_state_sha256": (b.get("economic_participation") or {}).get("state_sha256"),
            "embedded_manifest_count": len(manifests),
            "required_controller_attestation_count": len(required_controllers),
            "verified_controller_attestation_count": len(attested),
            "provider_independent": b.get("provider_independent") is True,
            "logical_state_not_database_bytes": b.get("database_bytes_are_not_authority") is True,
        }

    @staticmethod
    def _target_columns(db: sqlite3.Connection, schema_name: str, table: str) -> list[str]:
        rows = db.execute(f"PRAGMA {schema_name}.table_info({_quoted(table)})").fetchall()
        return [str(row[1]) for row in rows]

    @staticmethod
    def _assert_empty_compatible(db, schema_name: str, section: dict) -> None:
        for table, snapshot in section["tables"].items():
            target_columns = MarketStateRecovery._target_columns(db, schema_name, table)
            if target_columns != snapshot["columns"]:
                raise ValueError(f"target schema mismatch: {schema_name}.{table}")
            count = int(db.execute(
                f"SELECT COUNT(*) FROM {schema_name}.{_quoted(table)}"
            ).fetchone()[0])
            if count:
                raise ValueError(f"restore destination not empty: {schema_name}.{table}")

    @staticmethod
    def _restore_section(db, schema_name: str, section: dict) -> None:
        for table, snapshot in section["tables"].items():
            columns = list(snapshot["columns"])
            if not snapshot["rows"]:
                continue
            column_sql = ",".join(_quoted(c) for c in columns)
            placeholders = ",".join("?" for _ in columns)
            sql = (
                f"INSERT INTO {schema_name}.{_quoted(table)} "
                f"({column_sql}) VALUES ({placeholders})"
            )
            values = []
            for row in snapshot["rows"]:
                values.append(tuple(_encode_value(c, row.get(c)) for c in columns))
            db.executemany(sql, values)

    @staticmethod
    def restore(bundle: dict, exchange_path, economic_path, *, verify_manifest=None,
                verify_signature=None, verify_core_bundle=None) -> dict:
        verification = MarketStateRecovery.verify(
            bundle, verify_manifest=verify_manifest, verify_signature=verify_signature,
            verify_core_bundle=verify_core_bundle,
        )
        if not verification["valid"]:
            raise ValueError("market recovery bundle verification failed: " + ";".join(verification["failures"]))

        exchange_path = Path(exchange_path)
        economic_path = Path(economic_path)
        if not exchange_path.is_file() or not economic_path.is_file():
            raise FileNotFoundError("restore targets must be initialized EEP/EOPP databases")
        db = sqlite3.connect(exchange_path)
        try:
            db.execute("ATTACH DATABASE ? AS eopp", (str(economic_path),))
            MarketStateRecovery._assert_empty_compatible(db, "main", bundle["exchange"])
            MarketStateRecovery._assert_empty_compatible(db, "eopp", bundle["economic_participation"])
            db.execute("BEGIN IMMEDIATE")
            try:
                MarketStateRecovery._restore_section(db, "main", bundle["exchange"])
                MarketStateRecovery._restore_section(db, "eopp", bundle["economic_participation"])
                db.commit()
            except Exception:
                db.rollback()
                raise
        finally:
            db.close()
        restored_exchange = _snapshot_database(exchange_path, EEP_REQUIRED, EEP_OPTIONAL)
        restored_economic = _snapshot_database(economic_path, EOPP_REQUIRED)
        if restored_exchange["state_sha256"] != bundle["exchange"]["state_sha256"]:
            raise RuntimeError("restored EEP state root mismatch")
        if restored_economic["state_sha256"] != bundle["economic_participation"]["state_sha256"]:
            raise RuntimeError("restored EOPP state root mismatch")
        return {
            "schema": "entity-v3-market-recovery-result-v1",
            "restored": True,
            "exchange_state_sha256": restored_exchange["state_sha256"],
            "economic_state_sha256": restored_economic["state_sha256"],
            "bundle_semantic_sha256": bundle["semantic_sha256"],
            "atomic_cross_database_restore": True,
            "source_database_bytes_required": False,
        }

    @staticmethod
    def snapshot(exchange_path, economic_path) -> dict:
        exchange = _snapshot_database(Path(exchange_path), EEP_REQUIRED, EEP_OPTIONAL)
        economic = _snapshot_database(Path(economic_path), EOPP_REQUIRED)
        return {
            "exchange_state_sha256": exchange["state_sha256"],
            "economic_state_sha256": economic["state_sha256"],
            "exchange_rows": exchange["row_count"],
            "economic_rows": economic["row_count"],
        }
