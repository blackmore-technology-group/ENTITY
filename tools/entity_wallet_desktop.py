from __future__ import annotations
from pathlib import Path
import argparse, hashlib, html, importlib.util, json, os, sqlite3, sys, time, uuid

from PySide6 import QtCore, QtGui, QtWidgets

APP_NAME = "ENTITY Workspace — DataChips"
VERSION = "3.4.3-composer-qualification"

ROOT_BG = "#090B0E"
SIDEBAR_BG = "#0D1014"
PANEL_BG = "#11151A"
PANEL_2 = "#151A20"
BORDER = "#242B34"
TEXT = "#F3F0E8"
MUTED = "#8F99A7"
ACCENT = "#C9A96A"
ACCENT_DARK = "#7D6642"
GREEN = "#43D39E"
RED = "#FF6B78"
YELLOW = "#E3BC64"

def startup_stylesheet() -> str:
    return f"""
    * {{
        font-family: "Segoe UI";
        font-size: 10pt;
        color: {TEXT};
    }}
    QDialog, QMessageBox {{ background: {ROOT_BG}; }}
    QLabel {{ background: transparent; }}
    QLabel[class="brand"] {{ font-size: 26pt; font-weight: 800; letter-spacing: 2px; color: {TEXT}; }}
    QLabel[class="eyebrow"] {{ color: {ACCENT}; font-size: 8pt; font-weight: 700; letter-spacing: 1px; }}
    QLabel[class="dialogTitle"] {{ font-size: 18pt; font-weight: 700; }}
    QLabel[class="muted"] {{ color: {MUTED}; }}
    QLabel[class="chip"] {{
        background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 6px; padding: 10px; color: {MUTED};
    }}
    QLabel[class="tickerPreview"] {{
        background: {SIDEBAR_BG}; border: 1px solid {ACCENT_DARK}; border-radius: 6px;
        padding: 10px; color: {ACCENT}; font-family: Consolas; font-weight: 700;
    }}
    QFrame[class="panel"] {{ background: {PANEL_BG}; border: 1px solid {BORDER}; border-radius: 8px; }}
    QPushButton {{
        background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 6px;
        padding: 8px 13px; font-weight: 600;
    }}
    QPushButton:hover {{ border-color: {ACCENT_DARK}; background: #1A2027; }}
    QPushButton[primary="true"] {{
        background: {ACCENT}; color: #0C0E11; border-color: {ACCENT}; font-weight: 800;
    }}
    QLineEdit, QComboBox {{
        background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 5px; padding: 8px;
        selection-background-color: {ACCENT_DARK};
    }}
    QLineEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
    QComboBox QAbstractItemView {{
        background: {PANEL_2}; color: {TEXT}; border: 1px solid {BORDER};
        selection-background-color: #2A251A; selection-color: {TEXT}; outline: none;
    }}
    QListWidget {{
        background: {PANEL_2}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 6px;
        outline: none; padding: 4px;
    }}
    QListWidget::item {{
        background: {PANEL_2}; color: {TEXT}; padding: 8px 7px; border-bottom: 1px solid #1D232B;
    }}
    QListWidget::item:hover {{ background: #1A2027; color: {TEXT}; }}
    QListWidget::item:selected {{ background: #2A251A; color: {TEXT}; }}
    QCheckBox {{ spacing: 8px; }}
    """


def repo_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]

def load_module(name: str, relative: str):
    path = repo_root() / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

CLI = load_module("entity_wallet_v343_cli", "tools/entity_v3_4_cli.py")
WALLET = load_module("entity_wallet_model", "src/42_ENTITY_Wallet/canonical_wallet.py")
INGEST = load_module("entity_wallet_ingest", "src/42_ENTITY_Wallet/asset_ingest.py")
EXCHANGE = load_module("entity_wallet_exchange", "src/31_Profiles/exchange_protocol.py")
MARKET = load_module("entity_wallet_market", "src/45_ENTITY_Market/canonical_market_registry.py")
INTEL = load_module("entity_wallet_intelligence", "src/45_ENTITY_Market/economic_intelligence.py")
ONBOARDING = load_module("entity_wallet_onboarding", "src/42_ENTITY_Wallet/onboarding.py")
COMPOSER_UI = load_module("entity_wallet_datachip_ui", "tools/datachip_workspace_ui.py")

def default_state() -> Path:
    env = os.environ.get("ENTITY_STATE_DIR")
    if env:
        return Path(env).expanduser()
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Blackmore Technology Group" / "ENTITY"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Blackmore Technology Group" / "ENTITY"
    return Path.home() / ".local" / "share" / "blackmore-technology-group" / "entity"

def shorten(value: str | None, left: int = 10, right: int = 6) -> str:
    v = str(value or "")
    if len(v) <= left + right + 3:
        return v
    return v[:left] + "…" + v[-right:]

def manifests(state: Path) -> list[dict]:
    out = []
    root = state / "identity" / "manifests"
    if not root.is_dir():
        return out
    for p in sorted(root.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            out.append({"entity_id": d.get("entity_id"), "display_name": d.get("display_name") or d.get("entity_id")})
        except Exception:
            pass
    return [x for x in out if x["entity_id"]]

class Backend:
    def __init__(self, state: Path, entity_id: str):
        self.state = state
        self.entity_id = entity_id
        identity, fabric, profiles, origin, passports, packages, sdk, origin_status = CLI.runtime(state)
        self.identity = identity
        self.fabric = fabric
        self.profiles = profiles
        self.origin = origin
        self.passports = passports
        self.packages = packages
        self.sdk = sdk
        self.origin_status = origin_status
        self.rights = self.sdk.ingestion.rights
        self.identity_manifest = self.identity.load_manifest(entity_id)
        self.wallet = WALLET.EntityEconomicWallet(state)
        self.exchange = EXCHANGE.ExchangeProtocol(state, self.identity, self.fabric)
        self.market_registry = MARKET.EntityEconomicMarketRegistry(
            state, self.identity, self.fabric, self.exchange, self.rights, self.passports
        )
        self.intelligence = INTEL.EntityEconomicIntelligence(
            state, self.market_registry, self.fabric, self.passports
        )
        self.ingestor = INGEST.WalletAssetIngestor(state, CLI)
        self.wallet_record = self.wallet.ensure_wallet(
            entity_id, self.identity_manifest.get("display_name", "ENTITY") + " Wallet"
        )
        self.formula_set_path = self.state / "wallet" / "btdu_asset_formula_sets.sqlite"
        self._init_formula_set_registry()

    def snapshot(self):
        return self.wallet.snapshot(self.wallet_record["wallet_id"])

    def domains(self):
        return ["general"] + self.packages.list_packages()

    def asset_kinds(self, domain):
        return self.ingestor.asset_kinds(domain)

    def namespace_info(self) -> dict:
        return self.market_registry.suggest_namespace(self.entity_id)

    def namespace(self) -> str | None:
        return self.namespace_info().get("namespace")

    def asset_record(self, object_id: str) -> dict:
        return self.fabric.get_object(object_id)

    def asset_disclosure(self, object_id: str) -> dict | None:
        return self.market_registry.latest_asset_disclosure(object_id)

    def _init_formula_set_registry(self) -> None:
        self.formula_set_path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.formula_set_path, timeout=30.0)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
            CREATE TABLE IF NOT EXISTS asset_formula_sets(
              object_id TEXT PRIMARY KEY,
              controller_entity_id TEXT NOT NULL,
              universe_owner_entity_id TEXT NOT NULL,
              source_kind TEXT NOT NULL,
              source_path TEXT NOT NULL,
              source_name TEXT NOT NULL,
              directories_json TEXT NOT NULL,
              item_count INTEGER NOT NULL,
              logical_bytes INTEGER NOT NULL,
              manifest_sha256 TEXT NOT NULL,
              verified INTEGER NOT NULL,
              created_at_ms INTEGER NOT NULL,
              updated_at_ms INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS asset_formula_files(
              object_id TEXT NOT NULL,
              relative_path TEXT NOT NULL,
              formula_object_id TEXT NOT NULL,
              formula_sha256 TEXT NOT NULL,
              content_sha256 TEXT NOT NULL,
              size_bytes INTEGER NOT NULL,
              PRIMARY KEY(object_id,relative_path)
            );
            CREATE INDEX IF NOT EXISTS idx_asset_formula_files_formula
              ON asset_formula_files(formula_object_id);
            """)
            db.commit()
        finally:
            db.close()

    @staticmethod
    def _file_sha256(path: Path) -> tuple[str, int]:
        h = hashlib.sha256()
        size = 0
        with path.open("rb") as fh:
            for block in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(block)
                size += len(block)
        return h.hexdigest(), size

    def _formula_universe_owner(self, obj: dict) -> str:
        controller = str(obj.get("controller_entity_id") or "")
        try:
            binding = dict(self.latest_global_passport(obj["object_id"]).get("btdu_binding") or {})
        except Exception:
            binding = {}
        owner = str(binding.get("sovereign_entity_id") or "").strip()
        if owner:
            return owner
        btdu = CLI.btdu_mod
        canonical_ids = {
            btdu.BTDU_CANONICAL_OWNER_ENTITY_ID,
            btdu.BTG_STEWARD_ENTITY_ID,
            btdu.ENTITY_PROTOCOL_ENTITY_ID,
        }
        return btdu.BTDU_CANONICAL_OWNER_ENTITY_ID if controller in canonical_ids else controller

    def formula_storage_status(self, object_id: str) -> dict | None:
        db = sqlite3.connect(self.formula_set_path, timeout=5.0)
        db.row_factory = sqlite3.Row
        try:
            row = db.execute(
                "SELECT * FROM asset_formula_sets WHERE object_id=?",
                (str(object_id),),
            ).fetchone()
            if not row:
                return None
            files = [
                dict(r) for r in db.execute(
                    """SELECT relative_path,formula_object_id,formula_sha256,content_sha256,size_bytes
                       FROM asset_formula_files WHERE object_id=? ORDER BY relative_path""",
                    (str(object_id),),
                ).fetchall()
            ]
        finally:
            db.close()
        out = dict(row)
        out["verified"] = bool(out["verified"])
        out["directories"] = json.loads(out.pop("directories_json") or "[]")
        out["files"] = files
        return out

    def add_asset_to_formula_storage(self, object_id: str, source_path: str | Path, progress=None) -> dict:
        obj = self.asset_record(object_id)
        controller = str(obj.get("controller_entity_id") or "")
        if controller != self.entity_id:
            raise PermissionError("Only assets controlled by the active ENTITY identity can be upgraded to formula storage.")
        src = Path(source_path).expanduser().resolve()
        if src.is_file():
            source_kind = "FILE"
            source_name = src.name
            file_pairs = [(src.name, src)]
            directories = []
        elif src.is_dir():
            source_kind = "FOLDER"
            source_name = src.name
            directories = sorted(
                p.relative_to(src).as_posix()
                for p in src.rglob("*")
                if p.is_dir() and not p.is_symlink()
            )
            file_pairs = sorted(
                (p.relative_to(src).as_posix(), p)
                for p in src.rglob("*")
                if p.is_file() and not p.is_symlink()
            )
            if not file_pairs:
                raise ValueError("Selected folder contains no regular files.")
        else:
            raise FileNotFoundError(str(src))

        universe_owner = self._formula_universe_owner({**obj, "object_id": str(object_id)})
        root = self.state / "btdu" / universe_owner
        btdu = CLI.btdu_mod
        storage = btdu.BTDUStorageKernel(root / "storage")
        formulas = btdu.BTDUFormulaKernel(root / "formula", reservoir=storage)
        records = []
        total = len(file_pairs)
        try:
            for i, (rel, path) in enumerate(file_pairs, 1):
                if progress:
                    progress(i, total, rel)
                source_hash, source_size = self._file_sha256(path)
                formula = formulas.put_path(path)
                if str(formula.get("content_sha256") or "").lower() != source_hash:
                    raise RuntimeError(f"Formula content hash mismatch for {rel}")
                if int(formula.get("size_bytes") or -1) != int(source_size):
                    raise RuntimeError(f"Formula size mismatch for {rel}")
                verification = formulas.verify_object(str(formula["formula_object_id"]), deep=True)
                if not verification.get("pass"):
                    raise RuntimeError(f"Deep formula verification failed for {rel}: {verification.get('problems')}")
                records.append({
                    "relative_path": rel,
                    "formula_object_id": str(formula["formula_object_id"]),
                    "formula_sha256": str(formula["formula_sha256"]),
                    "content_sha256": source_hash,
                    "size_bytes": source_size,
                })
        finally:
            formulas.close()

        manifest = {
            "schema": "entity-wallet-btdu-asset-formula-set-v1",
            "object_id": str(object_id),
            "controller_entity_id": controller,
            "universe_owner_entity_id": universe_owner,
            "source_kind": source_kind,
            "source_name": source_name,
            "directories": directories,
            "files": records,
        }
        manifest_sha = hashlib.sha256(
            json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        now = int(time.time() * 1000)
        db = sqlite3.connect(self.formula_set_path, timeout=30.0)
        try:
            db.execute("PRAGMA busy_timeout=30000")
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT created_at_ms FROM asset_formula_sets WHERE object_id=?",
                (str(object_id),),
            ).fetchone()
            created = int(previous[0]) if previous else now
            db.execute("DELETE FROM asset_formula_files WHERE object_id=?", (str(object_id),))
            db.execute("DELETE FROM asset_formula_sets WHERE object_id=?", (str(object_id),))
            db.execute(
                """INSERT INTO asset_formula_sets(
                   object_id,controller_entity_id,universe_owner_entity_id,source_kind,source_path,source_name,
                   directories_json,item_count,logical_bytes,manifest_sha256,verified,created_at_ms,updated_at_ms)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(object_id), controller, universe_owner, source_kind, str(src), source_name,
                    json.dumps(directories, sort_keys=True), len(records),
                    sum(int(x["size_bytes"]) for x in records), manifest_sha, 1, created, now,
                ),
            )
            db.executemany(
                """INSERT INTO asset_formula_files(
                   object_id,relative_path,formula_object_id,formula_sha256,content_sha256,size_bytes)
                   VALUES(?,?,?,?,?,?)""",
                [
                    (
                        str(object_id), r["relative_path"], r["formula_object_id"],
                        r["formula_sha256"], r["content_sha256"], int(r["size_bytes"]),
                    )
                    for r in records
                ],
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
        return self.formula_storage_status(object_id)

    def export_formula_storage_set(self, object_id: str, destination: str | Path) -> dict:
        status = self.formula_storage_status(object_id)
        if not status or not status.get("verified"):
            raise RuntimeError("This asset has no verified formula-storage set.")
        obj = self.asset_record(object_id)
        if str(obj.get("controller_entity_id") or "") != self.entity_id:
            raise PermissionError("Only assets controlled by the active ENTITY identity can be reconstructed.")
        root = self.state / "btdu" / str(status["universe_owner_entity_id"])
        btdu = CLI.btdu_mod
        storage = btdu.BTDUStorageKernel(root / "storage")
        formulas = btdu.BTDUFormulaKernel(root / "formula", reservoir=storage)
        written = []
        destination = Path(destination)
        try:
            if status["source_kind"] == "FILE":
                if len(status["files"]) != 1:
                    raise RuntimeError("File formula set has invalid item count.")
                targets = [(status["files"][0], destination)]
            else:
                base = destination / status["source_name"]
                base.mkdir(parents=True, exist_ok=True)
                for rel_dir in status.get("directories") or []:
                    (base / Path(rel_dir)).mkdir(parents=True, exist_ok=True)
                targets = [(r, base / Path(r["relative_path"])) for r in status["files"]]

            for record, target in targets:
                result = formulas.materialize(record["formula_object_id"], target)
                if str(result["sha256"]).lower() != str(record["content_sha256"]).lower():
                    raise RuntimeError(f"Reconstructed hash mismatch for {record['relative_path']}")
                written.append({
                    "relative_path": record["relative_path"],
                    "path": str(target),
                    "bytes": int(result["bytes"]),
                    "sha256": str(result["sha256"]),
                    "formula_object_id": record["formula_object_id"],
                })
        finally:
            formulas.close()
        return {
            "schema": "entity-wallet-btdu-formula-set-export-v1",
            "object_id": str(object_id),
            "source_kind": status["source_kind"],
            "source_name": status["source_name"],
            "item_count": len(written),
            "bytes": sum(x["bytes"] for x in written),
            "manifest_sha256": status["manifest_sha256"],
            "verified": True,
            "formula_remains_authority": True,
            "files": written,
        }

    def instrument_product_plan(self, object_id: str) -> list[dict]:
        """Return the DCO factory's governed instrument plan for this current asset."""
        obj = self.asset_record(object_id)
        descriptor = obj.get("descriptor") or {}
        metadata = descriptor.get("metadata") or {}
        dco_code = str(metadata.get("dco_code") or "").strip()
        source_sha256 = str(obj.get("content_sha256") or "").strip()
        dbp = self.state / "dco_factory" / "entity_dco_factory.sqlite"
        if not dbp.exists():
            return []
        db = sqlite3.connect(dbp)
        db.row_factory = sqlite3.Row
        try:
            row = None
            if dco_code:
                row = db.execute(
                    "SELECT master_json FROM dco_masters WHERE dco_id=? LIMIT 1",
                    (dco_code,),
                ).fetchone()
            if row is None and source_sha256:
                row = db.execute(
                    "SELECT master_json FROM dco_masters WHERE source_sha256=? ORDER BY created_at_ms DESC LIMIT 1",
                    (source_sha256,),
                ).fetchone()
        finally:
            db.close()
        if not row:
            return []
        try:
            master = json.loads(row["master_json"] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
        physical = ((master.get("plan") or {}).get("physical_instruments") or [])
        return [dict(x) for x in physical if isinstance(x, dict)]

    def publish_asset_disclosure(self, object_id: str, options: dict) -> dict:
        return self.market_registry.publish_asset_disclosure(
            self.entity_id, object_id,
            description=options["description"],
            purpose=options.get("purpose", ""),
            capabilities=options.get("capabilities", []),
            contents=options.get("contents", []),
            intended_uses=options.get("intended_uses", []),
            limitations=options.get("limitations", []),
            dependencies=options.get("dependencies", []),
            validation_notes=options.get("validation_notes", []),
            release_notes=options.get("release_notes", ""),
            source_refs=options.get("source_refs", []),
        )

    def instrument_rights_profile(self, object_id: str) -> dict:
        gp = self.latest_global_passport(object_id)
        rp = self.rights.get(gp["rights_passport_id"])
        allowed = {}
        prohibited = {}
        other = {}
        for rule in rp.get("rights") or []:
            effect = str(rule.get("effect") or "").upper()
            for action in rule.get("actions") or []:
                token = str(action).strip().upper()
                if not token:
                    continue
                detail = {
                    "action": token,
                    "effect": effect,
                    "conditions": dict(rule.get("conditions") or {}),
                    "obligations": list(rule.get("obligations") or []),
                    "right_refs": list(rule.get("right_refs") or []),
                }
                if effect == "ALLOW":
                    allowed[token] = detail
                elif effect == "PROHIBIT":
                    prohibited[token] = detail
                else:
                    other[token] = detail
        return {
            "object_id": str(object_id),
            "global_passport_id": gp["passport_id"],
            "rights_passport_id": rp["passport_id"],
            "allowed_actions": sorted(allowed),
            "prohibited_actions": sorted(prohibited),
            "other_actions": sorted(other),
            "allowed": allowed,
            "prohibited": prohibited,
            "other": other,
        }

    def latest_global_passport(self, object_id: str) -> dict:
        dbp = self.state / "entity_v3_4_global_passports.sqlite"
        db = sqlite3.connect(dbp)
        db.row_factory = sqlite3.Row
        try:
            row = db.execute(
                """SELECT passport_id FROM global_passports WHERE object_id=?
                   ORDER BY created_at_ms DESC, passport_id DESC LIMIT 1""",
                (str(object_id),),
            ).fetchone()
        finally:
            db.close()
        if not row:
            raise KeyError("asset has no Global Passport")
        return self.passports.get(row["passport_id"])

    def global_passport_for_controller(self, object_id: str, controller_entity_id: str) -> dict | None:
        dbp = self.state / "entity_v3_4_global_passports.sqlite"
        db = sqlite3.connect(dbp)
        db.row_factory = sqlite3.Row
        try:
            row = db.execute(
                """SELECT passport_id FROM global_passports
                   WHERE object_id=? AND controller_entity_id=?
                   ORDER BY created_at_ms DESC, passport_id DESC LIMIT 1""",
                (str(object_id), str(controller_entity_id)),
            ).fetchone()
        finally:
            db.close()
        return None if not row else self.passports.get(row["passport_id"])

    def instruments(self) -> list[dict]:
        if not self.market_registry.path.exists():
            return []
        db = sqlite3.connect(self.market_registry.path)
        db.row_factory = sqlite3.Row
        try:
            rows = db.execute(
                """SELECT instrument_id FROM instrument_packages
                   WHERE issuer_entity_id=? AND status='ACTIVE'
                   ORDER BY created_at_ms, instrument_id""",
                (self.entity_id,),
            ).fetchall()
        finally:
            db.close()
        return [self.market_registry.instrument(r["instrument_id"]) for r in rows]

    def instrument_map_by_asset(self) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        if not self.market_registry.path.exists():
            return out
        db = sqlite3.connect(self.market_registry.path)
        db.row_factory = sqlite3.Row
        try:
            rows = db.execute(
                """SELECT instrument_id,underlying_dco_id FROM instrument_packages
                   WHERE issuer_entity_id=? AND status='ACTIVE'
                   ORDER BY created_at_ms""", (self.entity_id,)
            ).fetchall()
        finally:
            db.close()
        for r in rows:
            out.setdefault(r["underlying_dco_id"], []).append(self.market_registry.instrument(r["instrument_id"]))
        return out

    def venues(self) -> list[dict]:
        if not self.exchange.path.exists():
            return []
        db = sqlite3.connect(self.exchange.path)
        db.row_factory = sqlite3.Row
        try:
            rows = db.execute(
                "SELECT venue_id,name,jurisdiction,status FROM venues WHERE status='ACTIVE' ORDER BY name"
            ).fetchall()
        finally:
            db.close()
        return [dict(r) for r in rows]

    def market(self) -> list[dict]:
        rows = self.market_registry.active_market()
        if not rows:
            return []
        db = sqlite3.connect(self.exchange.path)
        db.row_factory = sqlite3.Row
        try:
            out = []
            for row in rows:
                e = db.execute(
                    "SELECT settlement_currency FROM instruments WHERE instrument_id=? AND status='ACTIVE'",
                    (row["instrument_id"],),
                ).fetchone()
                if not e:
                    continue
                d = dict(row)
                d["settlement_currency"] = e["settlement_currency"]
                d["market"] = self.wallet._market(db, d["instrument_id"])
                out.append(d)
            return out
        finally:
            db.close()

    def economic_metrics(self) -> list[dict]:
        seen = set()
        out = []
        for row in self.market_registry.active_market():
            iid = row["instrument_id"]
            if iid in seen:
                continue
            seen.add(iid)
            out.append(self.intelligence.instrument_metrics(iid))
        return out

    def economy_rollup(self, group_by="asset_class") -> dict:
        return self.intelligence.economy_rollup(group_by=group_by)

    def ingest(self, path, options):
        return self.ingestor.ingest_file(
            self.entity_id, path,
            title=options["title"], package=options["domain"],
            asset_kind=options.get("asset_kind") or None,
            jurisdiction=options.get("jurisdiction", ""),
            authority_basis=options["authority"],
            commodity_class=options["class"], measurement_unit=options["unit"],
            version=options.get("version") or "1.0",
            previous_object_id=options.get("parent_object_id") or None,
        )

    def export_asset_to_disk(self, object_id: str, output_path: str | Path) -> dict:
        """Reconstruct one controlled DCO from its authoritative BTDU formula onto disk."""
        obj = self.asset_record(object_id)
        controller = str(obj.get("controller_entity_id") or "")
        if controller != self.entity_id:
            raise PermissionError("Only assets controlled by the active ENTITY identity can be reconstructed.")
        gp = self.latest_global_passport(object_id)
        binding = dict(gp.get("btdu_binding") or {})
        object_ref = str(binding.get("object_ref") or "").strip()
        passport_formula_id = str(binding.get("formula_object_id") or "").strip()
        if not object_ref:
            raise RuntimeError("Selected asset has no reconstructive BTDU object binding.")

        btdu = CLI.btdu_mod
        canonical_ids = {
            btdu.BTDU_CANONICAL_OWNER_ENTITY_ID,
            btdu.BTG_STEWARD_ENTITY_ID,
            btdu.ENTITY_PROTOCOL_ENTITY_ID,
        }
        universe_owner = btdu.BTDU_CANONICAL_OWNER_ENTITY_ID if controller in canonical_ids else controller
        root = self.state / "btdu" / universe_owner
        index_path = root / "btdu_index.sqlite"
        if not index_path.exists():
            raise RuntimeError(f"BTDU universe is not installed for {universe_owner}.")

        db = sqlite3.connect(index_path, timeout=5.0)
        db.row_factory = sqlite3.Row
        try:
            row = db.execute(
                """SELECT formula_object_id,formula_sha256,authoritative
                   FROM object_formulas WHERE object_ref=?""",
                (object_ref,),
            ).fetchone()
        finally:
            db.close()
        if not row or int(row["authoritative"]) != 1:
            raise RuntimeError("BTDU formula binding is missing or not authoritative.")
        formula_id = str(row["formula_object_id"])
        if passport_formula_id and passport_formula_id != formula_id:
            raise RuntimeError("Global Passport formula binding does not match the live BTDU index.")

        storage = btdu.BTDUStorageKernel(root / "storage")
        formulas = btdu.BTDUFormulaKernel(root / "formula", reservoir=storage)
        result = formulas.materialize(formula_id, output_path)

        expected = str(obj.get("content_sha256") or "").strip().lower()
        bound_hash = str(binding.get("content_sha256") or "").strip().lower()
        actual = str(result.get("sha256") or "").strip().lower()
        if bound_hash and actual != bound_hash:
            Path(output_path).unlink(missing_ok=True)
            raise RuntimeError("Reconstructed file hash does not match the BTDU passport binding.")
        full_dco_payload = bool(expected and actual == expected)
        return {
            **dict(result),
            "schema": "entity-wallet-btdu-export-v1",
            "object_id": str(object_id),
            "btdu_object_ref": object_ref,
            "formula_object_id": formula_id,
            "formula_sha256": str(row["formula_sha256"]),
            "canonical_content_sha256": expected,
            "btdu_binding_content_sha256": bound_hash,
            "verified": True,
            "formula_remains_authority": True,
            "export_scope": "FULL_DCO_PAYLOAD" if full_dco_payload else "BOUND_COMPONENT_ONLY",
        }

    def transfer_activation_status(self, object_id: str) -> dict:
        obj = self.asset_record(object_id)
        controller = str(obj.get("controller_entity_id") or "")
        transfer = dict(obj.get("latest_controller_transfer") or {})
        if controller != self.entity_id:
            return {
                "object_id": str(object_id), "controlled_by_wallet": False,
                "required": False, "active": False, "reason": "NOT_CURRENT_CONTROLLER",
            }
        if not transfer or str(transfer.get("to_controller_entity_id") or "") != self.entity_id:
            return {
                "object_id": str(object_id), "controlled_by_wallet": True,
                "required": False, "active": True, "reason": "NOT_TRANSFERRED_IN",
            }
        try:
            gp = self.global_passport_for_controller(object_id, self.entity_id) or {}
        except Exception:
            gp = {}
        gp_controller = str(gp.get("controller_entity_id") or "")
        active = bool(gp and gp_controller == self.entity_id)
        return {
            "object_id": str(object_id),
            "controlled_by_wallet": True,
            "required": not active,
            "active": active,
            "reason": "ACTIVE" if active else "BUYER_PASSPORT_ACTIVATION_REQUIRED",
            "transfer_id": str(transfer.get("transfer_id") or ""),
            "from_controller_entity_id": str(transfer.get("from_controller_entity_id") or ""),
            "to_controller_entity_id": str(transfer.get("to_controller_entity_id") or ""),
            "trade_id": str(transfer.get("trade_id") or ""),
            "settlement_ref": transfer.get("settlement_ref"),
            "latest_global_passport_id": gp.get("passport_id"),
            "latest_global_passport_controller": gp_controller or None,
        }

    def activate_transferred_asset(self, object_id: str) -> dict:
        status = self.transfer_activation_status(object_id)
        if not status.get("controlled_by_wallet"):
            raise PermissionError("The active wallet is not the current DCO controller.")
        if status.get("active"):
            gp = self.global_passport_for_controller(object_id, self.entity_id)
            if not gp:
                raise RuntimeError("Buyer Global Passport activation state is inconsistent.")
            rp = self.rights.get(gp["rights_passport_id"])
            return {
                "schema": "entity-wallet-transferred-asset-activation-v1",
                "object_id": str(object_id),
                "transfer_id": status.get("transfer_id"),
                "activated": True,
                "idempotent_replay": True,
                "rights_passport_id": rp["passport_id"],
                "global_passport_id": gp["passport_id"],
                "controller_entity_id": self.entity_id,
            }
        transfer_id = str(status.get("transfer_id") or "")
        if not transfer_id:
            raise RuntimeError("Transferred asset has no controller-transfer receipt.")
        # The buyer must have its own private signing key locally. We never sign
        # a buyer passport with the seller's key or venue/operator key.
        self.identity.load_manifest(self.entity_id)
        old_gp = self.latest_global_passport(object_id)
        if str(old_gp.get("controller_entity_id") or "") == self.entity_id:
            raise RuntimeError("Buyer passport already exists but activation status did not resolve it.")
        old_rp = self.rights.get(old_gp["rights_passport_id"])
        version = "xfer-" + hashlib.sha256(transfer_id.encode("utf-8")).hexdigest()[:16]

        rp_db = sqlite3.connect(self.rights.path, timeout=5.0)
        rp_db.row_factory = sqlite3.Row
        try:
            existing_rp_row = rp_db.execute(
                """SELECT passport_id FROM passports
                   WHERE object_id=? AND controller_entity_id=? AND version=?""",
                (str(object_id), self.entity_id, version),
            ).fetchone()
        finally:
            rp_db.close()
        if existing_rp_row:
            new_rp = self.rights.get(existing_rp_row["passport_id"])
        else:
            authority_refs = sorted({
                *[str(x) for x in old_rp.get("authority_refs") or []],
                transfer_id,
            })
            provenance_refs = sorted({
                *[str(x) for x in old_rp.get("provenance_refs") or []],
                transfer_id,
            })
            # Deliberately conservative: whole-asset sale transfers ENTITY
            # controller authority and re-transfer authority. It does not
            # silently copy copyright, patent, commercialisation, training,
            # derivative or other historical licence rights.
            new_rp = self.rights.issue(
                self.entity_id,
                str(object_id),
                [{
                    "effect": "ALLOW",
                    "actions": ["CONTROL", "TRANSFER"],
                    "conditions": {
                        "authority_basis": "SETTLED_ASSET_TRANSFER",
                        "controller_transfer_id": transfer_id,
                        "trade_id": str(status.get("trade_id") or ""),
                    },
                    "obligations": [],
                    "right_refs": [transfer_id],
                }],
                version=version,
                authority_refs=authority_refs,
                jurisdiction_profile_refs=list(old_rp.get("jurisdiction_profile_refs") or []),
                semantic_refs=list(old_rp.get("semantic_refs") or []),
                custody=list(old_rp.get("custody") or []),
                provenance_refs=provenance_refs,
                disclosure_refs=list(old_rp.get("disclosure_refs") or []),
                privacy_profile=str(old_rp.get("privacy_profile") or "SELECTIVE_DISCLOSURE"),
                economic_terms=dict(old_rp.get("economic_terms") or {}),
                legal_classification=dict(old_rp.get("legal_classification") or {}),
            )

        gp_db = sqlite3.connect(self.passports.path, timeout=5.0)
        gp_db.row_factory = sqlite3.Row
        try:
            existing_gp_row = gp_db.execute(
                """SELECT passport_id FROM global_passports
                   WHERE object_id=? AND controller_entity_id=? AND version=?""",
                (str(object_id), self.entity_id, version),
            ).fetchone()
        finally:
            gp_db.close()
        if existing_gp_row:
            new_gp = self.passports.get(existing_gp_row["passport_id"])
        else:
            profile_refs = list((old_gp.get("profile_stack") or {}).get("profile_refs") or [])
            origin_ref = str((old_gp.get("protocol_origin") or {}).get("release_ref") or "") or None
            evidence_refs = sorted({
                *[str(x) for x in old_gp.get("evidence_refs") or []],
                transfer_id,
            })
            provenance_refs = sorted({
                *[str(x) for x in old_gp.get("provenance_refs") or []],
                transfer_id,
            })
            new_gp = self.passports.issue(
                self.entity_id,
                str(object_id),
                new_rp["passport_id"],
                profile_refs,
                version=version,
                evidence_refs=evidence_refs,
                provenance_refs=provenance_refs,
                jurisdiction_profile_refs=list(old_gp.get("jurisdiction_profile_refs") or []),
                standards_mappings=list(old_gp.get("standards_mappings") or []),
                economic_state=dict(old_gp.get("economic_state") or {}),
                industry_context=dict(old_gp.get("industry_context") or {}),
                protocol_release_ref=origin_ref,
                btdu_binding=dict(old_gp.get("btdu_binding") or {}) or None,
            )
        if not self.rights.verify(new_rp).get("valid"):
            raise RuntimeError("Buyer Rights Passport verification failed.")
        if not self.passports.verify(new_gp).get("valid"):
            raise RuntimeError("Buyer Global Passport verification failed.")
        return {
            "schema": "entity-wallet-transferred-asset-activation-v1",
            "object_id": str(object_id),
            "transfer_id": transfer_id,
            "activated": True,
            "idempotent_replay": False,
            "rights_passport_id": new_rp["passport_id"],
            "global_passport_id": new_gp["passport_id"],
            "controller_entity_id": self.entity_id,
            "rights_actions": ["CONTROL", "TRANSFER"],
            "historical_seller_passports_preserved": True,
            "seller_rights_not_silently_inherited": True,
        }

    def create_instrument(self, object_id: str, options: dict) -> dict:
        gp = self.latest_global_passport(object_id)
        rights_profile = self.instrument_rights_profile(object_id)
        requested = {str(x).strip().upper() for x in options.get("actions") or [] if str(x).strip()}
        allowed = set(rights_profile["allowed_actions"])
        prohibited = set(rights_profile["prohibited_actions"])
        if not requested:
            raise ValueError("At least one Rights Passport action must be selected.")
        if requested & prohibited:
            bad = ", ".join(sorted(requested & prohibited))
            raise PermissionError(f"Selected action(s) are prohibited by the Rights Passport: {bad}")
        if not requested.issubset(allowed):
            missing = ", ".join(sorted(requested - allowed))
            permitted = ", ".join(rights_profile["allowed_actions"]) or "none"
            raise PermissionError(
                f"Selected action(s) are not granted by the Rights Passport: {missing}. "
                f"Permitted actions: {permitted}"
            )
        asset_transfer = str(options["instrument_class"]).upper() == "ASSET_TRANSFER"
        if asset_transfer:
            if requested != {"TRANSFER"}:
                raise ValueError("Whole-asset sale requires exactly the TRANSFER Rights Passport action.")
            formula_set = self.formula_storage_status(object_id)
            if not formula_set or not formula_set.get("verified"):
                raise RuntimeError(
                    "Whole-asset sale requires a verified complete formula-storage set. "
                    "Use 'Add to Formula Storage' on the asset first."
                )
            if int(options["supply"]) != 1 or str(options["fungibility"]).upper() != "NON-FUNGIBLE"                     or int(options["divisibility"]) != 0 or bool(options["transferable"]):
                raise ValueError("Whole-asset transfer must be one indivisible, non-fungible, non-secondary-transferable unit.")
        return self.market_registry.create_instrument(
            self.entity_id, object_id,
            instrument_name=options["name"], display_symbol=options["symbol"],
            instrument_class=options["instrument_class"], rights_class=options["rights_class"],
            rights={"actions": options["actions"]}, supply=options["supply"],
            rights_passport_id=gp["rights_passport_id"], global_passport_id=gp["passport_id"],
            settlement_currency=options["currency"], jurisdiction=options["jurisdiction"],
            series=options["series"], fungibility=options["fungibility"],
            divisibility=options["divisibility"], transferable=options["transferable"],
            duration_ms=options.get("duration_ms"),
            delivery_mode="ASSET_CONTROL" if asset_transfer else "ENTITLEMENT",
            transfer_rules={
                "wallet_defined": True,
                "underlying_controller_transfer_on_settlement": bool(asset_transfer),
                "requires_verified_formula_storage": bool(asset_transfer),
            },
            economic_terms={"market_value_created_by_issuance": False},
            royalty_terms={"automatic_protocol_royalty_bps": 0},
            buyer_receives=options["buyer_receives"],
            buyer_does_not_receive=options["buyer_does_not_receive"],
            evidence_refs=gp.get("evidence_refs") or [],
            namespace=options.get("namespace") or None,
        )

    def create_listing(self, instrument_id: str, options: dict) -> dict:
        return self.market_registry.create_listing(
            self.entity_id, instrument_id, options["venue_id"],
            market_id=options["market_id"], quote_unit=options["quote_unit"],
            trade_mode=options["trade_mode"], settlement_method=options["settlement_method"],
            minimum_quantity=options["minimum_quantity"],
            quantity_precision=options["quantity_precision"], price_precision=options["price_precision"],
            pricing_method=options["pricing_method"], listing_series=options["listing_series"],
            tick_size=options["tick_size"],
        )

    def submit_order(self, row: dict, side: str, quantity: int, limit_price: int):
        venue = row.get("venue_id")
        if not venue:
            raise ValueError("This instrument has no active market listing.")
        order = self.exchange.submit_order(
            venue, row["instrument_id"], self.entity_id, side, quantity, limit_price,
            nonce="wallet-" + uuid.uuid4().hex, tif="GTC"
        )
        trades = self.exchange.match_order_book(venue, row["instrument_id"])
        return {"order": order, "trades": trades}

    def pending_settlements(self) -> list[dict]:
        with self.exchange._db() as db:
            rows = db.execute(
                """SELECT t.trade_id,t.venue_id,t.instrument_id,t.buyer,t.seller,t.quantity,t.price,
                          t.execution_model,t.status,c.amount_units,c.currency,c.payment_ref,c.external_verified,
                          i.instrument_class,i.underlying_object_id,i.delivery_mode
                   FROM trades t
                   JOIN clearing c ON c.trade_id=t.trade_id
                   JOIN instruments i ON i.instrument_id=t.instrument_id
                   WHERE t.status='EXECUTED_UNSETTLED' AND c.status='PENDING'
                     AND (t.buyer=? OR t.seller=?)
                   ORDER BY t.created_at_ms DESC,t.trade_id""",
                (self.entity_id, self.entity_id),
            ).fetchall()
        out = []
        for row in rows:
            d = dict(row)
            d["role"] = "SELLER" if d["seller"] == self.entity_id else "BUYER"
            try:
                pkg = self.market_registry.instrument(d["instrument_id"])
                d["market_identifier"] = pkg.get("market_identifier")
                d["instrument_name"] = pkg.get("instrument_name")
            except Exception:
                d["market_identifier"] = None
                d["instrument_name"] = d["instrument_id"]
            d["delivery_kind"] = (
                "WHOLE DCO + FORMULA STORAGE"
                if d["instrument_class"] == "ASSET_TRANSFER"
                else "RIGHTS ENTITLEMENT"
            )
            out.append(d)
        return out

    def complete_settlement(self, trade_id: str, payment_ref: str) -> dict:
        trade_id = str(trade_id)
        payment_ref = str(payment_ref or "").strip()
        if not payment_ref:
            raise ValueError("A payment/settlement reference is required.")
        rows = [x for x in self.pending_settlements() if x["trade_id"] == trade_id]
        if not rows:
            raise KeyError("Pending settlement not found.")
        pending = rows[0]
        if pending["seller"] != self.entity_id:
            raise PermissionError("The seller/controller must confirm payment and complete delivery.")
        result = self.exchange.settle_trade(
            trade_id, payment_ref=payment_ref, external_verified=False, payment_attestation_id=None
        )
        transfer = result.get("asset_transfer")
        if transfer:
            delivery = self.market_registry.finalize_asset_transfer_delivery(
                pending["instrument_id"], trade_id, transfer
            )
            db = sqlite3.connect(self.formula_set_path, timeout=30.0)
            try:
                db.execute(
                    "UPDATE asset_formula_sets SET controller_entity_id=?,updated_at_ms=? WHERE object_id=?",
                    (str(transfer["to_controller_entity_id"]), int(time.time() * 1000), str(transfer["object_id"])),
                )
                db.commit()
            finally:
                db.close()
            result["market_delivery"] = delivery
            result["delivery_status"] = "DCO_CONTROLLER_AND_FORMULA_SET_DELIVERED"
        else:
            result["delivery_status"] = "RIGHTS_ENTITLEMENT_DELIVERED"
        result["seller_confirmed_payment_reference"] = True
        result["external_payment_verification"] = False
        return result

class Ui:
    @staticmethod
    def label(text="", cls=""):
        w = QtWidgets.QLabel(text)
        if cls:
            w.setProperty("class", cls)
        return w

    @staticmethod
    def button(text, primary=False):
        b = QtWidgets.QPushButton(text)
        b.setCursor(QtCore.Qt.PointingHandCursor)
        b.setProperty("primary", primary)
        return b

    @staticmethod
    def table(headers):
        t = QtWidgets.QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.verticalHeader().setVisible(False)
        t.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        t.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        t.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        t.setShowGrid(False)
        t.setAlternatingRowColors(False)
        t.setWordWrap(False)
        t.setTextElideMode(QtCore.Qt.ElideRight)
        t.verticalHeader().setDefaultSectionSize(38)
        t.horizontalHeader().setStretchLastSection(True)
        t.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        t.setSortingEnabled(False)
        return t

    @staticmethod
    def fill_table(table, rows):
        table.setRowCount(0)
        for row in rows:
            i = table.rowCount()
            table.insertRow(i)
            for j, value in enumerate(row):
                item = QtWidgets.QTableWidgetItem("" if value is None else str(value))
                item.setData(QtCore.Qt.UserRole, value)
                table.setItem(i, j, item)
        for i in range(table.rowCount()):
            table.setRowHeight(i, 38)

class MetricCard(QtWidgets.QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setProperty("class", "metricCard")
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(18, 15, 18, 15)
        lay.setSpacing(5)
        title_label = Ui.label(title.upper(), "eyebrow")
        self.value = Ui.label("—", "metric")
        self.note = Ui.label("", "muted")
        lay.addWidget(title_label)
        lay.addWidget(self.value)
        lay.addWidget(self.note)

class EmptyState(QtWidgets.QFrame):
    def __init__(self, title, body):
        super().__init__()
        self.setProperty("class", "empty")
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(28, 28, 28, 28)
        lay.addWidget(Ui.label(title, "emptyTitle"))
        body_label = Ui.label(body, "muted")
        body_label.setWordWrap(True)
        lay.addWidget(body_label)

class EntitySetupDialog(QtWidgets.QDialog):
    def __init__(self, parent, onboarding):
        super().__init__(parent)
        self.onboarding = onboarding
        self.profile = None
        self.setWindowTitle("Create your ENTITY identity")
        self.resize(760, 690)
        self.setMinimumSize(690, 610)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        layout.addWidget(Ui.label("WELCOME TO ENTITY", "eyebrow"))
        layout.addWidget(Ui.label("Create your sovereign identity", "dialogTitle"))
        intro = Ui.label(
            "This creates your own cryptographic ENTITY identity and public .entity name. "
            "Your device receives a separate device identity; device information never becomes your human or company identity.",
            "muted"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        principal_box = QtWidgets.QFrame()
        principal_box.setProperty("class", "panel")
        pf = QtWidgets.QFormLayout(principal_box)
        pf.setContentsMargins(18, 18, 18, 18)
        pf.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        self.principal_type = QtWidgets.QComboBox()
        self.principal_type.addItems(["person", "business", "organization", "project", "community", "family"])
        self.principal_name = QtWidgets.QLineEdit()
        self.principal_name.setPlaceholderText("Jane Smith")
        self.principal_public = QtWidgets.QLineEdit()
        self.principal_public.setPlaceholderText("jane.smith")
        self.principal_preview = Ui.label("jane.smith.entity", "tickerPreview")
        pf.addRow("Identity type", self.principal_type)
        pf.addRow("Public display name", self.principal_name)
        pf.addRow("Public ENTITY name", self.principal_public)
        pf.addRow("Address preview", self.principal_preview)
        layout.addWidget(principal_box)

        self.add_org = QtWidgets.QCheckBox("Create an operating organization/business under this identity")
        self.add_org.setChecked(False)
        layout.addWidget(self.add_org)

        self.org_box = QtWidgets.QFrame()
        self.org_box.setProperty("class", "panel")
        of = QtWidgets.QFormLayout(self.org_box)
        of.setContentsMargins(18, 18, 18, 18)
        of.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.org_type = QtWidgets.QComboBox()
        self.org_type.addItems(["business", "organization", "project"])
        self.org_name = QtWidgets.QLineEdit()
        self.org_name.setPlaceholderText("Acme Corporation")
        self.org_public = QtWidgets.QLineEdit()
        self.org_public.setPlaceholderText("acme")
        self.org_preview = Ui.label("acme.entity", "tickerPreview")
        self.operate_as_org = QtWidgets.QCheckBox("Open the wallet as this operating entity")
        self.operate_as_org.setChecked(True)
        of.addRow("Entity type", self.org_type)
        of.addRow("Organization name", self.org_name)
        of.addRow("Public ENTITY name", self.org_public)
        of.addRow("Address preview", self.org_preview)
        of.addRow("", self.operate_as_org)
        layout.addWidget(self.org_box)
        self.org_box.setVisible(False)

        self.lineage_preview = Ui.label("LINEAGE  —", "chip")
        self.lineage_preview.setWordWrap(True)
        layout.addWidget(self.lineage_preview)

        note = Ui.label(
            "Public names are human-readable aliases. The immutable ENTITY ID and signatures remain authoritative. "
            "A local name conflict does not let one user impersonate another.",
            "muted"
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()

        buttons = QtWidgets.QHBoxLayout()
        cancel = Ui.button("Exit")
        create = Ui.button("Create ENTITY and wallet", True)
        cancel.clicked.connect(self.reject)
        create.clicked.connect(self.create_identity)
        buttons.addWidget(cancel)
        buttons.addStretch()
        buttons.addWidget(create)
        layout.addLayout(buttons)

        self.add_org.toggled.connect(self.org_box.setVisible)
        self.add_org.toggled.connect(self.update_preview)
        self.principal_public.textChanged.connect(self.update_preview)
        self.org_public.textChanged.connect(self.update_preview)
        self.update_preview()

    @staticmethod
    def _address(text):
        raw = str(text or "").strip().lower()
        if raw.endswith(".entity"):
            raw = raw[:-7]
        return (raw + ".entity") if raw else "—"

    def update_preview(self):
        p = self._address(self.principal_public.text())
        self.principal_preview.setText(p)
        if self.add_org.isChecked():
            o = self._address(self.org_public.text())
            self.org_preview.setText(o)
            self.lineage_preview.setText(f"LINEAGE  {p}  →  {o}")
        else:
            self.lineage_preview.setText(f"LINEAGE  {p}")

    def create_identity(self):
        if not self.principal_name.text().strip() or not self.principal_public.text().strip():
            QtWidgets.QMessageBox.warning(self, "ENTITY setup", "Display name and public ENTITY name are required.")
            return
        if self.add_org.isChecked() and (not self.org_name.text().strip() or not self.org_public.text().strip()):
            QtWidgets.QMessageBox.warning(
                self, "ENTITY setup",
                "Organization name and public ENTITY name are required when an operating organization is enabled."
            )
            return
        try:
            self.profile = self.onboarding.create_profile(
                principal_display_name=self.principal_name.text().strip(),
                principal_public_name=self.principal_public.text().strip(),
                principal_entity_type=self.principal_type.currentText(),
                organization_display_name=self.org_name.text().strip() if self.add_org.isChecked() else None,
                organization_public_name=self.org_public.text().strip() if self.add_org.isChecked() else None,
                organization_entity_type=self.org_type.currentText(),
                operate_as_organization=self.operate_as_org.isChecked(),
            )
            auth = self.onboarding.authenticate(self.profile)
            if not auth.get("authenticated"):
                raise RuntimeError("new identity was created but device-bound authentication failed")
            self.accept()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "ENTITY setup failed", str(exc))


class EntityLoginDialog(QtWidgets.QDialog):
    def __init__(self, parent, onboarding):
        super().__init__(parent)
        self.onboarding = onboarding
        self.profile = None
        self.create_new = False
        self.profiles = onboarding.list_profiles()
        self.setWindowTitle("Unlock ENTITY")
        self.resize(620, 390)
        self.setMinimumWidth(580)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        layout.addWidget(Ui.label("ENTITY", "brand"))
        layout.addWidget(Ui.label("SOVEREIGN WALLET ACCESS", "eyebrow"))
        layout.addWidget(Ui.label("Unlock your local ENTITY identity", "dialogTitle"))
        note = Ui.label(
            "ENTITY uses possession of your local signing identity plus the bound device identity. "
            "The operating-system account name is not treated as your ENTITY identity.",
            "muted"
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self.selector = QtWidgets.QComboBox()
        for profile in self.profiles:
            active = onboarding.identity.load_manifest(profile["active_entity_id"])
            self.selector.addItem(
                f"{profile['display_path']}   ·   {active['display_name']}",
                profile["profile_id"]
            )
        layout.addWidget(self.selector)

        self.detail = Ui.label("", "chip")
        self.detail.setWordWrap(True)
        layout.addWidget(self.detail)
        self.selector.currentIndexChanged.connect(self.update_detail)
        self.update_detail()
        layout.addStretch()

        buttons = QtWidgets.QHBoxLayout()
        create = Ui.button("Create another identity")
        unlock = Ui.button("Unlock wallet", True)
        create.clicked.connect(self.choose_create)
        unlock.clicked.connect(self.unlock)
        buttons.addWidget(create)
        buttons.addStretch()
        buttons.addWidget(unlock)
        layout.addLayout(buttons)

    def update_detail(self):
        idx = self.selector.currentIndex()
        if idx < 0 or idx >= len(self.profiles):
            self.detail.setText("No local wallet profile.")
            return
        p = self.profiles[idx]
        self.detail.setText(
            f"LINEAGE  {p['display_path']}\n"
            f"LOGIN  device-bound signing key\n"
            f"ACTIVE ENTITY  {shorten(p['active_entity_id'], 14, 10)}"
        )

    def choose_create(self):
        self.create_new = True
        self.accept()

    def unlock(self):
        idx = self.selector.currentIndex()
        if idx < 0 or idx >= len(self.profiles):
            return
        profile = self.profiles[idx]
        auth = self.onboarding.authenticate(profile)
        if not auth.get("authenticated"):
            QtWidgets.QMessageBox.critical(
                self, "ENTITY unlock failed",
                "The local signing identity or bound device could not authenticate this wallet.\n\n"
                + str(auth.get("reason") or "authentication failed")
                + ("\n\nRecovery or device re-binding is required." if auth.get("recovery_or_rebind_required") else "")
            )
            return
        self.onboarding.set_active(profile["profile_id"])
        self.profile = profile
        self.accept()


class AssetDisclosureDialog(QtWidgets.QDialog):
    def __init__(self, parent, asset: dict, current: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Asset Information")
        self.resize(820, 820)
        self.setMinimumSize(720, 680)
        self.result_data = None
        current = current or {}
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.addWidget(Ui.label("SIGNED ASSET DISCLOSURE", "dialogTitle"))
        title = Ui.label(asset.get("title") or asset.get("object_id"), "tickerHero")
        title.setWordWrap(True)
        layout.addWidget(title)
        note = Ui.label(
            "This is the buyer-facing description of the underlying DCO. It is signed and versioned. "
            "It describes the asset; it does not expand the Rights Passport or manufacture market value.",
            "muted"
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        host = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(host)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        def area(value="", height=86):
            w = QtWidgets.QPlainTextEdit(str(value or ""))
            w.setMinimumHeight(height)
            return w

        def lines(values):
            return "\n".join(str(x) for x in (values or []))

        self.description = area(current.get("description"), 130)
        self.purpose = area(current.get("purpose"), 80)
        self.capabilities = area(lines(current.get("capabilities")), 90)
        self.contents = area(lines(current.get("contents")), 90)
        self.intended = area(lines(current.get("intended_uses")), 90)
        self.limitations = area(lines(current.get("limitations")), 90)
        self.dependencies = area(lines(current.get("dependencies")), 80)
        self.validation = area(lines(current.get("validation_notes")), 90)
        self.release_notes = area(current.get("release_notes"), 80)
        self.source_refs = area(lines(current.get("source_refs")), 70)

        for label, widget in [
            ("Detailed asset description", self.description),
            ("Purpose / problem addressed", self.purpose),
            ("Key capabilities\n(one per line)", self.capabilities),
            ("Included content / components\n(one per line)", self.contents),
            ("Intended uses\n(one per line)", self.intended),
            ("Known limitations / exclusions\n(one per line)", self.limitations),
            ("Dependencies / prerequisites\n(one per line)", self.dependencies),
            ("Validation / qualification notes\n(one per line)", self.validation),
            ("Version / release notes", self.release_notes),
            ("Supporting source references\n(one per line)", self.source_refs),
        ]:
            form.addRow(label, widget)
        scroll.setWidget(host)
        layout.addWidget(scroll, 1)

        boundary = Ui.label(
            "ENTITY records this as an issuer statement. Evidence and passport references remain independently inspectable.",
            "muted"
        )
        boundary.setWordWrap(True)
        layout.addWidget(boundary)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch()
        cancel = Ui.button("Cancel")
        publish = Ui.button("Sign and publish asset information", True)
        cancel.clicked.connect(self.reject)
        publish.clicked.connect(self.accept_data)
        buttons.addWidget(cancel)
        buttons.addWidget(publish)
        layout.addLayout(buttons)

    @staticmethod
    def _items(editor):
        return [x.strip() for x in editor.toPlainText().splitlines() if x.strip()]

    def accept_data(self):
        description = self.description.toPlainText().strip()
        if len(description) < 20:
            QtWidgets.QMessageBox.warning(
                self, "Asset description",
                "Provide a meaningful buyer-facing asset description before publishing."
            )
            return
        self.result_data = {
            "description": description,
            "purpose": self.purpose.toPlainText().strip(),
            "capabilities": self._items(self.capabilities),
            "contents": self._items(self.contents),
            "intended_uses": self._items(self.intended),
            "limitations": self._items(self.limitations),
            "dependencies": self._items(self.dependencies),
            "validation_notes": self._items(self.validation),
            "release_notes": self.release_notes.toPlainText().strip(),
            "source_refs": self._items(self.source_refs),
        }
        self.accept()


class ListingInformationDialog(QtWidgets.QDialog):
    def __init__(self, parent, market_identifier: str, markdown: str):
        super().__init__(parent)
        self.setWindowTitle(f"Listing Information Sheet · {market_identifier}")
        self.resize(1060, 820)
        self.setMinimumSize(820, 620)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        head = QtWidgets.QHBoxLayout()
        head.addWidget(Ui.label("LISTING INFORMATION SHEET", "dialogTitle"))
        head.addStretch()
        head.addWidget(Ui.label(market_identifier, "tickerHero"))
        layout.addLayout(head)
        browser = QtWidgets.QTextBrowser()
        browser.setProperty("class", "detail")
        browser.setOpenExternalLinks(False)
        browser.setMarkdown(markdown)
        layout.addWidget(browser, 1)
        foot = QtWidgets.QHBoxLayout()
        foot.addWidget(Ui.label(
            "Buyer-facing disclosure snapshot · canonical passports and instrument records remain authoritative.",
            "muted"
        ))
        foot.addStretch()
        close = Ui.button("Close", True)
        close.clicked.connect(self.accept)
        foot.addWidget(close)
        layout.addLayout(foot)


class InstrumentDialog(QtWidgets.QDialog):
    ACTION_META = {
        "TRAIN": ("Training", "TRN", "TRAINING"),
        "FINE_TUNE": ("Fine-tuning", "FTN", "FINE_TUNING"),
        "INFER": ("Inference", "INF", "INFERENCE"),
        "EVALUATE": ("Evaluation", "EVL", "EVALUATION"),
        "BENCHMARK": ("Benchmark", "BNCH", "BENCHMARK"),
        "CERTIFY": ("Certification", "CERT", "CERTIFICATION"),
        "COMPUTE": ("Compute-to-data", "CMP", "COMPUTE"),
        "DERIVE": ("Derivative", "DER", "DERIVATIVE"),
        "OEM_DEPLOY": ("OEM deployment", "OEM", "OEM"),
        "COMMERCIALIZE": ("Commercialization", "COM", "COMMERCIAL"),
        "EXECUTE": ("Execution", "EXE", "EXECUTION"),
        "CONTROL": ("Control", "CTL", "CONTROL"),
        "MODIFY": ("Modification", "MOD", "MODIFICATION"),
        "TRANSFER": ("Transfer", "XFR", "TRANSFER"),
        "COPY": ("Copy", "CPY", "COPY"),
        "READ": ("Read/access", "ACC", "ACCESS"),
        "INSPECT": ("Inspection", "INSP", "INSPECTION"),
    }

    def __init__(self, parent, asset, namespace, rights_profile):
        super().__init__(parent)
        self.setWindowTitle("Issue Economic Instrument")
        self.setMinimumSize(620, 520)
        screen = QtWidgets.QApplication.screenAt(QtGui.QCursor.pos()) or QtWidgets.QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            target_w = min(800, max(620, available.width() - 100))
            target_h = min(760, max(520, available.height() - 120))
            self.resize(target_w, target_h)
            self.move(
                available.left() + max(0, (available.width() - target_w) // 2),
                available.top() + max(0, (available.height() - target_h) // 2),
            )
        else:
            self.resize(760, 680)
        self.setSizeGripEnabled(True)
        self.result_data = None
        self.asset = asset
        self.rights_profile = rights_profile
        self.instrument_plan = [dict(x) for x in (asset.get("instrument_plan") or []) if isinstance(x, dict)]
        self._updating = False

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        layout.addWidget(Ui.label("ISSUE ECONOMIC INSTRUMENT", "dialogTitle"))
        subtitle = Ui.label(
            "The DCO Rights Passport is authoritative. Select a subset of rights already granted "
            "to this asset; the wallet cannot invent or broaden them.",
            "muted")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        passport_box = QtWidgets.QFrame()
        passport_box.setProperty("class", "panel")
        pb = QtWidgets.QVBoxLayout(passport_box)
        pb.setContentsMargins(16, 13, 16, 13)
        pb.addWidget(Ui.label("RIGHTS PASSPORT", "eyebrow"))
        pb.addWidget(Ui.label(
            f"{shorten(rights_profile['rights_passport_id'], 22, 12)}  ·  "
            f"{len(rights_profile['allowed_actions'])} selectable action(s)",
            "monoMuted"
        ))
        layout.addWidget(passport_box)

        if not rights_profile["allowed_actions"]:
            warning = Ui.label(
                "This DCO currently has no ALLOW actions in its Rights Passport. "
                "No economic instrument can be issued until the asset rights are explicitly authorized.",
                "muted")
            warning.setWordWrap(True)
            layout.addWidget(warning)

        scroll = QtWidgets.QScrollArea()
        scroll.setObjectName("instrumentScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        scroll.viewport().setObjectName("instrumentScrollViewport")
        scroll_host = QtWidgets.QWidget()
        scroll_host.setObjectName("instrumentScrollHost")

        dark_palette = scroll_host.palette()
        dark_palette.setColor(QtGui.QPalette.Window, QtGui.QColor(ROOT_BG))
        dark_palette.setColor(QtGui.QPalette.Base, QtGui.QColor(ROOT_BG))
        dark_palette.setColor(QtGui.QPalette.Text, QtGui.QColor(TEXT))
        dark_palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(TEXT))
        scroll.viewport().setPalette(dark_palette)
        scroll.viewport().setAutoFillBackground(True)
        scroll_host.setPalette(dark_palette)
        scroll_host.setAutoFillBackground(True)

        scroll.setStyleSheet(f"""
            QScrollArea#instrumentScrollArea {{
                background: {ROOT_BG};
                border: none;
            }}
            QWidget#instrumentScrollViewport,
            QWidget#instrumentScrollHost {{
                background: {ROOT_BG};
                color: {TEXT};
            }}
            QScrollBar:vertical {{
                background: {ROOT_BG};
                width: 12px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: #303844;
                min-height: 30px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)

        scroll_layout = QtWidgets.QVBoxLayout(scroll_host)
        scroll_layout.setContentsMargins(0, 0, 8, 0)
        scroll_layout.setSpacing(12)
        scroll.setWidget(scroll_host)
        layout.addWidget(scroll, 1)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignLeft)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        form.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)

        self.namespace = QtWidgets.QLineEdit(namespace or "")
        self.symbol = QtWidgets.QLineEdit("")
        self.symbol.setReadOnly(True)
        self.symbol.setToolTip(
            "Generated automatically from the current DCO identity, selected Rights Passport action(s), and series."
        )
        self.name = QtWidgets.QLineEdit("")
        self.name.setReadOnly(True)
        self.name.setToolTip(
            "Generated from the DCO's canonical asset name and the selected governed Rights Class."
        )
        self.iclass = QtWidgets.QComboBox()
        self.iclass.addItems([
            "SPOT_LICENSE","SUBSCRIPTION","COMPUTE_TO_DATA",
            "PROCUREMENT","CONTRIBUTION","SECONDARY_LICENSE","ASSET_TRANSFER"
        ])
        self.rclass = QtWidgets.QComboBox()
        self.rclass.setToolTip(
            "Rights Classes come from this DCO's governed instrument plan and are filtered by the selected Rights Passport actions."
        )

        self.actions = QtWidgets.QListWidget()
        self.actions.setMinimumHeight(150)
        self.actions.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        for action in rights_profile["allowed_actions"]:
            detail = rights_profile["allowed"].get(action, {})
            label = self.ACTION_META.get(action, (action.replace("_", " ").title(), action[:5], action))[0]
            conditions = detail.get("conditions") or {}
            obligations = detail.get("obligations") or []
            text = f"{action}  —  {label}"
            if conditions:
                text += "  ·  conditions apply"
            if obligations:
                text += "  ·  obligations apply"
            item = QtWidgets.QListWidgetItem(text)
            item.setData(QtCore.Qt.UserRole, action)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setForeground(QtGui.QBrush(QtGui.QColor(TEXT)))
            item.setBackground(QtGui.QBrush(QtGui.QColor(PANEL_2)))
            item.setCheckState(QtCore.Qt.Unchecked)
            tip = []
            if conditions:
                tip.append("Conditions: " + json.dumps(conditions, sort_keys=True))
            if obligations:
                tip.append("Obligations: " + ", ".join(str(x) for x in obligations))
            item.setToolTip("\n".join(tip) if tip else "Granted by the current Rights Passport.")
            self.actions.addItem(item)

        self.supply = QtWidgets.QSpinBox()
        self.supply.setRange(1, 2_000_000_000)
        self.supply.setValue(1)
        self.currency = QtWidgets.QLineEdit("CAD")
        self.jurisdiction = QtWidgets.QLineEdit("CA")
        self.series = QtWidgets.QSpinBox()
        self.series.setRange(1, 999999)
        self.series.setValue(1)
        self.fungibility = QtWidgets.QComboBox()
        self.fungibility.addItems(["FUNGIBLE","SERIES-FUNGIBLE","NON-FUNGIBLE"])
        self.divisibility = QtWidgets.QSpinBox()
        self.divisibility.setRange(0, 9)
        self.transferable = QtWidgets.QCheckBox("Secondary transfer permitted")
        self.receives = QtWidgets.QPlainTextEdit("")
        self.receives.setMinimumHeight(70)
        self.excludes = QtWidgets.QPlainTextEdit(
            "Ownership of the underlying DCO\n"
            "Copyright ownership\n"
            "Rights not stated in the Rights Passport"
        )
        self.excludes.setMinimumHeight(70)

        for label, widget in [
            ("Automatic instrument name", self.name),
            ("Issuer namespace", self.namespace),
            ("Automatic ticker / symbol", self.symbol),
            ("EEP class", self.iclass),
            ("Rights class", self.rclass),
            ("Rights Passport actions", self.actions),
            ("Supply", self.supply),
            ("Settlement currency", self.currency),
            ("Jurisdiction", self.jurisdiction),
            ("Series", self.series),
            ("Fungibility", self.fungibility),
            ("Divisibility", self.divisibility),
            ("Transferability", self.transferable),
            ("Buyer receives", self.receives),
            ("Buyer does NOT receive", self.excludes),
        ]:
            form.addRow(label, widget)
        scroll_layout.addLayout(form)

        excluded = []
        if rights_profile["prohibited_actions"]:
            excluded.append("PROHIBITED: " + ", ".join(rights_profile["prohibited_actions"]))
        if rights_profile["other_actions"]:
            excluded.append("NOT DIRECTLY ISSUABLE: " + ", ".join(rights_profile["other_actions"]))
        if excluded:
            boundary = QtWidgets.QFrame()
            boundary.setProperty("class", "notice")
            bl = QtWidgets.QVBoxLayout(boundary)
            bl.setContentsMargins(14, 10, 14, 10)
            for line in excluded:
                note = Ui.label(line, "muted")
                note.setWordWrap(True)
                bl.addWidget(note)
            scroll_layout.addWidget(boundary)

        self.preview = Ui.label("", "tickerPreview")
        scroll_layout.addWidget(self.preview)
        scroll_layout.addStretch()
        self.namespace.textChanged.connect(self._preview)
        self.actions.itemChanged.connect(self._rights_changed)
        self.rclass.currentIndexChanged.connect(self._rights_class_changed)
        self.series.valueChanged.connect(lambda _value: self._rights_class_changed())

        buttons = QtWidgets.QHBoxLayout()
        buttons.setContentsMargins(0, 8, 0, 0)
        buttons.addStretch()
        cancel = Ui.button("Cancel")
        create = Ui.button("Issue instrument", True)
        cancel.setMinimumHeight(40)
        create.setMinimumHeight(40)
        create.setDefault(True)
        create.setAutoDefault(True)
        create.setEnabled(bool(rights_profile["allowed_actions"]))
        cancel.clicked.connect(self.reject)
        create.clicked.connect(self.accept_data)
        buttons.addWidget(cancel)
        buttons.addWidget(create)
        layout.addLayout(buttons)

        self.form_scroll = scroll
        self.cancel_button = cancel
        self.issue_button = create

        self._rights_changed()

    def selected_actions(self):
        return [
            str(self.actions.item(i).data(QtCore.Qt.UserRole))
            for i in range(self.actions.count())
            if self.actions.item(i).checkState() == QtCore.Qt.Checked
        ]

    def _base_symbol(self):
        short_name = str(self.asset.get("short_name") or "").upper()
        if short_name:
            compact = "".join(ch for ch in short_name if ch.isalnum())
            if compact:
                return compact[:10]
        dco_code = str(self.asset.get("dco_code") or "").upper()
        if dco_code:
            compact = "".join(ch for ch in dco_code if ch.isalnum())
            if compact:
                return compact[:10]
        title = str(self.asset.get("title") or "ASSET").upper()
        words = [w for w in "".join(ch if ch.isalnum() else " " for ch in title).split() if w]
        ignored = {
            "BLACKMORE","INDUSTRIAL","REAL","TIME","THE","AND","OF",
            "ASSET","DATASET","ENGINE","DIGITAL","ROBOTICS"
        }
        useful = [w for w in words if w not in ignored]
        if not useful:
            useful = words
        if len(useful) == 1:
            base = useful[0][:10]
        else:
            initials = "".join(w[0] for w in useful[:5])
            base = initials if len(initials) >= 3 else "".join(useful)[:10]
        return base[:10] or "ASSET"

    @staticmethod
    def _token(value):
        text = "".join(ch if ch.isalnum() else "_" for ch in str(value or "").upper())
        return "_".join(part for part in text.split("_") if part)

    def _plan_option(self, plan):
        archetype = self._token(plan.get("archetype"))
        variant = self._token(plan.get("variant"))
        if not archetype:
            return None
        value = archetype + (f"_{variant}" if variant else "")
        label = archetype.replace("_", " ").title()
        if variant:
            label += f" · {str(plan.get('variant')).upper()}"
        return {"value": value, "label": label, "plan": dict(plan)}

    def _eligible_plan_options(self):
        allowed = {self._token(a) for a in self.rights_profile.get("allowed_actions") or []}
        prohibited = {self._token(a) for a in self.rights_profile.get("prohibited_actions") or []}
        options = []
        seen = set()
        for plan in self.instrument_plan:
            plan_actions = {self._token(a) for a in (plan.get("actions") or []) if self._token(a)}
            if not plan_actions or not plan_actions.issubset(allowed) or plan_actions & prohibited:
                continue
            option = self._plan_option(plan)
            if not option or option["value"] in seen:
                continue
            seen.add(option["value"])
            option["plan_actions"] = sorted(plan_actions)
            options.append(option)
        options.sort(key=lambda x: x["label"])
        return options

    def _matching_plan_options(self, actions):
        selected = {self._token(a) for a in actions if self._token(a)}
        if not selected:
            return []
        return [
            option for option in self._eligible_plan_options()
            if selected == set(option.get("plan_actions") or [])
        ]

    def _populate_rights_classes(self, actions):
        previous = self._selected_rights_class()
        self.rclass.blockSignals(True)
        self.rclass.clear()
        if self.instrument_plan:
            options = self._eligible_plan_options()
            selected_tokens = {self._token(a) for a in actions}
            allowed_tokens = {self._token(a) for a in self.rights_profile.get("allowed_actions") or []}
            if selected_tokens == {"TRANSFER"} and "TRANSFER" in allowed_tokens:
                options = options + [{
                    "value": "ASSET_TRANSFER",
                    "label": "Whole Asset Transfer",
                    "plan": None,
                    "plan_actions": ["TRANSFER"],
                }]
            self.rclass.addItem("Choose governed Rights Class", None)
            for option in options:
                self.rclass.addItem(option["label"], option)
            self.rclass.setEnabled(bool(options))
            matches = [
                option for option in options
                if selected_tokens == set(option.get("plan_actions") or [])
            ]
            selected_index = 0
            if previous:
                for i in range(1, self.rclass.count()):
                    data = self.rclass.itemData(i)
                    if (
                        isinstance(data, dict)
                        and data.get("value") == previous
                        and any(m.get("value") == previous for m in matches)
                    ):
                        selected_index = i
                        break
            if selected_index == 0 and len(matches) == 1:
                target = matches[0]["value"]
                for i in range(1, self.rclass.count()):
                    data = self.rclass.itemData(i)
                    if isinstance(data, dict) and data.get("value") == target:
                        selected_index = i
                        break
            self.rclass.setCurrentIndex(selected_index)
        elif not actions:
            self.rclass.addItem("Select Rights Passport action(s) first", None)
            self.rclass.setEnabled(False)
        else:
            self.rclass.setEnabled(True)
            metas = [self.ACTION_META.get(a, (a.replace("_", " ").title(), a[:5], a)) for a in actions]
            if len(actions) == 1:
                label, _suffix, value = metas[0]
                if self._token(actions[0]) == "TRANSFER":
                    option = {"value": "ASSET_TRANSFER", "label": "Whole Asset Transfer", "plan": None}
                else:
                    option = {"value": self._token(value), "label": f"{label} Rights", "plan": None}
            else:
                option = {"value": "BUNDLED_RIGHTS", "label": "Bundled Rights", "plan": None}
            self.rclass.addItem(option["label"], option)
        self.rclass.blockSignals(False)

    def _selected_rights_class(self):
        data = self.rclass.currentData()
        if isinstance(data, dict):
            return str(data.get("value") or "").strip().upper()
        return ""

    def _selected_plan(self):
        data = self.rclass.currentData()
        if isinstance(data, dict) and isinstance(data.get("plan"), dict):
            return data["plan"]
        return None

    def _rights_class_code(self, rights_class):
        rc = self._token(rights_class)
        known = {
            "EVALUATION": "EVL", "RUNTIME_USE": "RUN", "INFERENCE": "INF",
            "TRAINING": "TRN", "COMPUTE_TO_DATA": "CTD", "ENTERPRISE_API": "API",
            "COMMERCIAL_DERIVATIVE": "CDR", "OEM_EMBEDDED": "OEM",
            "FIELD_OF_USE": "FOU", "REDISTRIBUTION": "RED",
            "SYNTHETIC_DERIVED_DATA": "SDD", "CONTRIBUTOR_PARTICIPATION": "CTR",
            "COMMERCIAL": "COM", "DERIVATIVE": "DER", "EXECUTION": "EXE",
            "CONTROL": "CTL", "ACCESS": "ACC", "INSPECTION": "INSP",
            "BUNDLED_RIGHTS": "BND", "ASSET_TRANSFER": "OWN",
        }
        if rc.startswith("REGIONAL_EXCLUSIVITY_"):
            region = rc[len("REGIONAL_EXCLUSIVITY_"):]
            return f"REX-{region.replace('_', '-')}"
        if rc in known:
            return known[rc]
        words = [x for x in rc.split("_") if x]
        if not words:
            return "RGT"
        if len(words) == 1:
            return words[0][:5]
        initials = "".join(w[0] for w in words)
        return initials[:5] or "RGT"

    def _generated_symbol(self, actions=None):
        rights_class = self._selected_rights_class()
        if not rights_class:
            return ""
        base = self._base_symbol()
        suffix = self._rights_class_code(rights_class)
        symbol = f"{base}-{suffix}"
        if self.series.value() > 1:
            symbol += f"-S{self.series.value()}"
        return symbol[:32]

    def _rights_changed(self, item=None):
        if self._updating:
            return
        actions = self.selected_actions()
        self._populate_rights_classes(actions)
        receives = []
        for action in actions:
            detail = self.rights_profile["allowed"].get(action, {})
            line = f"{action} right under the current Rights Passport"
            if detail.get("conditions"):
                line += " (subject to passport conditions)"
            if detail.get("obligations"):
                line += " (subject to passport obligations)"
            receives.append(line)
        self.receives.setPlainText("\n".join(receives))
        self._rights_class_changed()

    def _rights_class_changed(self, _index=None):
        rights_class = self._selected_rights_class()
        data = self.rclass.currentData()
        plan = self._selected_plan()
        if rights_class and plan:
            target_actions = {self._token(a) for a in (plan.get("actions") or []) if self._token(a)}
            current_actions = {self._token(a) for a in self.selected_actions()}
            if current_actions != target_actions:
                self._updating = True
                try:
                    for i in range(self.actions.count()):
                        item = self.actions.item(i)
                        action = self._token(item.data(QtCore.Qt.UserRole))
                        item.setCheckState(
                            QtCore.Qt.Checked if action in target_actions else QtCore.Qt.Unchecked
                        )
                finally:
                    self._updating = False

        actions = self.selected_actions()
        is_asset_transfer = rights_class == "ASSET_TRANSFER"
        if is_asset_transfer:
            idx = self.iclass.findText("ASSET_TRANSFER")
            if idx >= 0:
                self.iclass.setCurrentIndex(idx)
            self.supply.setValue(1); self.supply.setEnabled(False)
            self.fungibility.setCurrentText("NON-FUNGIBLE"); self.fungibility.setEnabled(False)
            self.divisibility.setValue(0); self.divisibility.setEnabled(False)
            self.transferable.setChecked(False); self.transferable.setEnabled(False)
            self.receives.setPlainText(
                "Controller/ownership position of the underlying DCO in ENTITY\n"
                "Verified BTDU formula-storage set associated with the DCO\n"
                "Right to reconstruct the delivered formula-stored asset under the transferred controller"
            )
            self.excludes.setPlainText(
                "Copyright ownership unless separately stated\n"
                "Patent or trademark rights unless separately stated\n"
                "Rights not stated in the Rights Passport or sale terms"
            )
        else:
            self.supply.setEnabled(True)
            self.fungibility.setEnabled(True)
            self.divisibility.setEnabled(True)
            self.transferable.setEnabled(True)
            if self.iclass.currentText() == "ASSET_TRANSFER":
                self.iclass.setCurrentText("SPOT_LICENSE")
            self.excludes.setPlainText(
                "Ownership of the underlying DCO\n"
                "Copyright ownership\n"
                "Rights not stated in the Rights Passport"
            )
        if not actions or not rights_class or not isinstance(data, dict):
            self.name.setText("")
            self.symbol.setText("")
            self.receives.setPlainText("")
            self._preview()
            return

        if not is_asset_transfer:
            receives = []
            for action in actions:
                detail = self.rights_profile["allowed"].get(action, {})
                line = f"{action} right under the current Rights Passport"
                if detail.get("conditions"):
                    line += " (subject to passport conditions)"
                if detail.get("obligations"):
                    line += " (subject to passport obligations)"
                receives.append(line)
            self.receives.setPlainText("\n".join(receives))

        if plan:
            eep_class = str(plan.get("eep_class") or "").strip().upper()
            idx = self.iclass.findText(eep_class)
            if idx >= 0:
                self.iclass.setCurrentIndex(idx)
        title = str(self.asset.get("title") or "Asset").strip()
        rights_label = str(data.get("label") or rights_class.replace("_", " ").title()).strip()
        self.name.setText(
            f"{title} — Whole Asset Transfer"
            if is_asset_transfer else f"{title} — {rights_label} Rights"
        )
        self.symbol.setText(self._generated_symbol(actions))
        self._preview()

    def _preview(self):
        ns = (self.namespace.text().strip() or "NAMESPACE").upper()
        sym = (self.symbol.text().strip() or "SELECT-RIGHT").upper()
        self.preview.setText(f"MARKET IDENTIFIER PREVIEW   {ns}:{sym}")

    def accept_data(self):
        actions = self.selected_actions()
        if not actions:
            QtWidgets.QMessageBox.warning(
                self, "Instrument",
                "Select at least one action granted by the DCO's Rights Passport."
            )
            return
        allowed = set(self.rights_profile["allowed_actions"])
        if not set(actions).issubset(allowed):
            QtWidgets.QMessageBox.critical(
                self, "Rights Passport",
                "The selected actions are no longer a valid subset of the current Rights Passport."
            )
            return
        rights_class = self._selected_rights_class()
        if not rights_class:
            QtWidgets.QMessageBox.warning(
                self, "Rights Class",
                "Choose a governed Rights Class that matches the selected Rights Passport actions."
            )
            return
        plan = self._selected_plan()
        if plan:
            selected = {self._token(a) for a in actions}
            plan_actions = {self._token(a) for a in (plan.get("actions") or [])}
            if not selected.issubset(plan_actions):
                QtWidgets.QMessageBox.critical(
                    self, "Rights Class",
                    "The selected Rights Class does not authorize the selected Rights Passport action set."
                )
                return
        symbol = self._generated_symbol(actions)
        self.symbol.setText(symbol)
        self._preview()
        if not symbol or not self.name.text().strip():
            QtWidgets.QMessageBox.warning(self, "Instrument", "Automatic instrument identity could not be generated.")
            return

        is_asset_transfer = self.iclass.currentText() == "ASSET_TRANSFER"
        if is_asset_transfer:
            if set(actions) != {"TRANSFER"} or rights_class != "ASSET_TRANSFER":
                QtWidgets.QMessageBox.critical(
                    self, "Whole Asset Transfer",
                    "Whole-asset sale requires exactly the TRANSFER Rights Passport action and Whole Asset Transfer rights class."
                )
                return
            self.supply.setValue(1)
            self.fungibility.setCurrentText("NON-FUNGIBLE")
            self.divisibility.setValue(0)
            self.transferable.setChecked(False)
        self.result_data = {
            "name": self.name.text().strip(),
            "namespace": self.namespace.text().strip(),
            "symbol": symbol,
            "instrument_class": self.iclass.currentText(),
            "rights_class": rights_class,
            "actions": actions,
            "supply": self.supply.value(),
            "currency": self.currency.text().strip(),
            "jurisdiction": self.jurisdiction.text().strip(),
            "series": self.series.value(),
            "fungibility": self.fungibility.currentText(),
            "divisibility": self.divisibility.value(),
            "transferable": self.transferable.isChecked(),
            "duration_ms": None,
            "buyer_receives": [
                x.strip() for x in self.receives.toPlainText().splitlines() if x.strip()
            ],
            "buyer_does_not_receive": [
                x.strip() for x in self.excludes.toPlainText().splitlines() if x.strip()
            ],
        }
        self.accept()

class ListingDialog(QtWidgets.QDialog):
    def __init__(self, parent, backend: Backend, instrument: dict):
        super().__init__(parent)
        self.setWindowTitle("Create Market Listing")
        self.setMinimumWidth(600)
        self.result_data = None
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(Ui.label("CREATE MARKET LISTING", "dialogTitle"))
        layout.addWidget(Ui.label(instrument["market_identifier"], "tickerHero"))
        layout.addWidget(Ui.label(
            "A listing is separate from the canonical instrument. It binds a buyer-facing Listing Information Sheet and machine manifest.",
            "muted"))
        form = QtWidgets.QFormLayout()
        self.venue = QtWidgets.QComboBox()
        self.venues = backend.venues()
        for v in self.venues:
            self.venue.addItem(f"{v['name']}  ·  {v['jurisdiction']}", v["venue_id"])
        self.market_id = QtWidgets.QLineEdit("ENTITY-MKT")
        self.quote = QtWidgets.QLineEdit("CAD")
        self.mode = QtWidgets.QComboBox(); self.mode.addItems(["ORDER_BOOK","CALL_AUCTION","RFQ"])
        self.settlement = QtWidgets.QComboBox()
        if str(instrument.get("instrument_class") or "").upper() == "ASSET_TRANSFER":
            self.settlement.addItems(["PAYMENT_VERSUS_ASSET"])
        else:
            self.settlement.addItems(["PAYMENT_VERSUS_RIGHT"])
        self.min_qty = QtWidgets.QSpinBox(); self.min_qty.setRange(1, 2_000_000_000); self.min_qty.setValue(1)
        self.qprec = QtWidgets.QSpinBox(); self.qprec.setRange(0, 9)
        self.pprec = QtWidgets.QSpinBox(); self.pprec.setRange(0, 9)
        self.pricing = QtWidgets.QComboBox(); self.pricing.addItems(["ORDER_BOOK","CALL_AUCTION","RFQ"])
        self.series = QtWidgets.QSpinBox(); self.series.setRange(1, 999999); self.series.setValue(1)
        self.tick = QtWidgets.QSpinBox(); self.tick.setRange(1, 2_000_000_000); self.tick.setValue(1)
        for label, widget in [
            ("Venue", self.venue), ("Market ID", self.market_id), ("Quote unit", self.quote),
            ("Trade mode", self.mode), ("Settlement", self.settlement), ("Minimum quantity", self.min_qty),
            ("Quantity precision", self.qprec), ("Price precision", self.pprec),
            ("Pricing method", self.pricing), ("Listing series", self.series), ("Tick size", self.tick),
        ]:
            form.addRow(label, widget)
        layout.addLayout(form)
        buttons = QtWidgets.QHBoxLayout(); buttons.addStretch()
        cancel = Ui.button("Cancel"); create = Ui.button("Create listing", True)
        cancel.clicked.connect(self.reject); create.clicked.connect(self.accept_data)
        buttons.addWidget(cancel); buttons.addWidget(create); layout.addLayout(buttons)

    def accept_data(self):
        if self.venue.count() == 0:
            QtWidgets.QMessageBox.warning(self, "Listing", "No active ENTITY-compatible venue is available.")
            return
        self.result_data = {
            "venue_id": self.venue.currentData(), "market_id": self.market_id.text().strip(),
            "quote_unit": self.quote.text().strip(), "trade_mode": self.mode.currentText(),
            "settlement_method": self.settlement.currentText(), "minimum_quantity": self.min_qty.value(),
            "quantity_precision": self.qprec.value(), "price_precision": self.pprec.value(),
            "pricing_method": self.pricing.currentText(), "listing_series": self.series.value(),
            "tick_size": self.tick.value(),
        }
        self.accept()

class OrderDialog(QtWidgets.QDialog):
    def __init__(self, parent, row, side):
        super().__init__(parent)
        self.setWindowTitle(f"{side.title()} {row.get('market_identifier') or row['instrument_id']}")
        self.result_data = None
        m = row["market"]
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(Ui.label(side, "eyebrow"))
        layout.addWidget(Ui.label(row.get("market_identifier") or row["instrument_id"], "tickerHero"))
        form = QtWidgets.QFormLayout()
        self.qty = QtWidgets.QSpinBox(); self.qty.setRange(1, 2_000_000_000); self.qty.setValue(1)
        self.price = QtWidgets.QSpinBox(); self.price.setRange(0, 2_000_000_000)
        default = m.get("ask") if side == "BUY" else m.get("bid")
        if default is not None: self.price.setValue(int(default))
        form.addRow("Quantity", self.qty); form.addRow(f"Limit price ({row['settlement_currency']})", self.price)
        layout.addLayout(form)
        layout.addWidget(Ui.label(f"Bid {m.get('bid') or '—'}    Ask {m.get('ask') or '—'}    Last {m.get('last') or '—'}", "muted"))
        buttons = QtWidgets.QHBoxLayout(); buttons.addStretch()
        cancel = Ui.button("Cancel"); submit = Ui.button(f"Submit {side}", True)
        cancel.clicked.connect(self.reject); submit.clicked.connect(self.accept_data)
        buttons.addWidget(cancel); buttons.addWidget(submit); layout.addLayout(buttons)

    def accept_data(self):
        self.result_data = (self.qty.value(), self.price.value())
        self.accept()

class AssetIngestDialog(QtWidgets.QDialog):
    def __init__(self, parent, path: Path, backend: Backend):
        super().__init__(parent)
        self.setWindowTitle("Ingest Digital Asset")
        self.setMinimumWidth(650)
        self.result_data = None
        self.backend = backend
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(Ui.label("INGEST DIGITAL ASSET", "dialogTitle"))
        layout.addWidget(Ui.label(str(path), "monoMuted"))
        form = QtWidgets.QFormLayout()
        self.title = QtWidgets.QLineEdit(path.name)
        self.domain = QtWidgets.QComboBox(); self.domain.addItems(backend.domains())
        self.kind = QtWidgets.QComboBox()
        self.juris = QtWidgets.QLineEdit("")
        self.cclass = QtWidgets.QLineEdit("DIGITAL_ASSET")
        self.unit = QtWidgets.QLineEdit("ASSET")
        self.authority = QtWidgets.QLineEdit(f"CONTROLLER_ENTITY:{backend.entity_id}")
        self.version = QtWidgets.QLineEdit("1.0")
        self.parent_id = QtWidgets.QLineEdit("")
        self.attest = QtWidgets.QCheckBox("I have authority to register this asset and attest its provenance.")
        for label, widget in [
            ("Asset title", self.title), ("Domain profile", self.domain), ("Asset kind", self.kind),
            ("Jurisdiction", self.juris), ("Commodity class", self.cclass), ("Measurement unit", self.unit),
            ("Authority basis", self.authority), ("Passport version", self.version),
            ("Parent object ID", self.parent_id), ("Authority attestation", self.attest),
        ]:
            form.addRow(label, widget)
        layout.addLayout(form)
        layout.addWidget(Ui.label(
            "Creates the governed DCO + evidence + Rights Passport + Global Passport + BTDU binding. No ticker, instrument, listing or price is created automatically.",
            "muted"))
        self.domain.currentTextChanged.connect(self._domain)
        self._domain(self.domain.currentText())
        buttons = QtWidgets.QHBoxLayout(); buttons.addStretch()
        cancel = Ui.button("Cancel"); ingest = Ui.button("Ingest asset", True)
        cancel.clicked.connect(self.reject); ingest.clicked.connect(self.accept_data)
        buttons.addWidget(cancel); buttons.addWidget(ingest); layout.addLayout(buttons)

    def _domain(self, domain):
        self.kind.clear()
        kinds = self.backend.asset_kinds(domain)
        self.kind.addItems(kinds)
        self.cclass.setText("DIGITAL_ASSET" if domain == "general" else domain.upper().replace("-", "_") + "_ASSET")

    def accept_data(self):
        if not self.attest.isChecked():
            QtWidgets.QMessageBox.warning(self, "Authority", "Authority attestation is required.")
            return
        if self.domain.currentText() != "general" and not self.juris.text().strip():
            QtWidgets.QMessageBox.warning(self, "Jurisdiction", "Domain package ingest requires an explicit jurisdiction.")
            return
        self.result_data = {
            "title": self.title.text().strip(), "domain": self.domain.currentText(),
            "asset_kind": self.kind.currentText(), "jurisdiction": self.juris.text().strip(),
            "class": self.cclass.text().strip(), "unit": self.unit.text().strip(),
            "authority": self.authority.text().strip(), "version": self.version.text().strip(),
            "parent_object_id": self.parent_id.text().strip(),
        }
        self.accept()

class WalletWindow(QtWidgets.QMainWindow):
    NAV = [
        ("workspace", "DATACHIP WORKSPACE"), ("composer", "VISUAL COMPOSER"),
        ("assets", "CHIP LIBRARY / ASSETS"), ("instruments", "RIGHTS INSTRUMENTS"),
        ("market", "CAPABILITY EXCHANGE"), ("intelligence", "MARKET ANALYTICS"),
        ("orders", "SETTLEMENTS"), ("overview", "TREASURY OVERVIEW"),
    ]

    def __init__(self, state: Path, entity_id: str, wallet_profile: dict | None = None):
        super().__init__()
        self.state = state
        self.entity_id = entity_id
        self.wallet_profile = wallet_profile
        self.backend = Backend(state, entity_id)
        self.snapshot_data = {}
        self.assets_rows: list[dict] = []
        self.instruments_rows: list[dict] = []
        self.market_rows: list[dict] = []
        self.metrics_rows: list[dict] = []
        self.settlements_rows: list[dict] = []
        self.setWindowTitle(f"{APP_NAME} · Engineering Qualification")
        self.resize(1560, 940)
        self.setMinimumSize(1180, 720)
        self._build()
        self._apply_style()
        self.refresh()
        self.navigate("workspace")

    def _build(self):
        root = QtWidgets.QWidget(); self.setCentralWidget(root)
        outer = QtWidgets.QHBoxLayout(root); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        side = QtWidgets.QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(238)
        sl = QtWidgets.QVBoxLayout(side); sl.setContentsMargins(18, 22, 18, 20); sl.setSpacing(7)
        sl.addWidget(Ui.label("ENTITY", "brand"))
        sl.addWidget(Ui.label("UNIVERSAL DATACHIP WORKSPACE", "brandSub"))
        sl.addSpacing(24)
        self.nav_buttons = {}
        for key, label in self.NAV:
            b = QtWidgets.QPushButton(label); b.setCheckable(True); b.setCursor(QtCore.Qt.PointingHandCursor)
            b.setProperty("nav", True); b.clicked.connect(lambda checked=False, k=key: self.navigate(k))
            self.nav_buttons[key] = b; sl.addWidget(b)
        sl.addStretch()
        sl.addWidget(Ui.label("SOVEREIGN LOCAL STATE", "eyebrow"))
        sl.addWidget(Ui.label("DATACHIP COMPOSER · ALPHA\nUnverified rights remain denied\nMarkets and treasury preserved", "sidebarFoot"))
        outer.addWidget(side)

        body = QtWidgets.QWidget(); bl = QtWidgets.QVBoxLayout(body)
        bl.setContentsMargins(26, 18, 26, 22); bl.setSpacing(14)
        header = QtWidgets.QHBoxLayout()
        titlebox = QtWidgets.QVBoxLayout()
        self.page_title = Ui.label("", "pageTitle")
        self.page_sub = Ui.label("", "pageSub")
        titlebox.addWidget(self.page_title); titlebox.addWidget(self.page_sub)
        header.addLayout(titlebox); header.addStretch()
        self.lineage_chip = Ui.label("", "chip")
        self.namespace_chip = Ui.label("", "chip")
        self.market_chip = Ui.label("", "chip")
        self.identity_chip = Ui.label("", "identityChip")
        header.addWidget(self.lineage_chip); header.addWidget(self.namespace_chip); header.addWidget(self.market_chip); header.addWidget(self.identity_chip)
        bl.addLayout(header)

        self.tape = Ui.label("", "tape")
        bl.addWidget(self.tape)

        self.stack = QtWidgets.QStackedWidget()
        bl.addWidget(self.stack, 1)
        outer.addWidget(body, 1)

        self.pages = {}
        self.pages["workspace"] = self._workspace_page()
        self.pages["composer"] = self._composer_page()
        self.pages["overview"] = self._overview_page()
        self.pages["assets"] = self._assets_page()
        self.pages["instruments"] = self._instruments_page()
        self.pages["market"] = self._market_page()
        self.pages["intelligence"] = self._intelligence_page()
        self.pages["orders"] = self._orders_page()
        for key, _ in self.NAV:
            self.stack.addWidget(self.pages[key])

    def _workspace_page(self):
        """DataChip-first workspace, not a rebranded stock-trading chart."""
        p = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(p)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)
        message = QtWidgets.QFrame()
        message.setProperty("class", "panel")
        ml = QtWidgets.QVBoxLayout(message)
        ml.setContentsMargins(22, 20, 22, 20)
        ml.addWidget(Ui.label("BUILD · CONNECT · VERIFY · DEPLOY", "sectionTitle"))
        title = Ui.label("The ENTITY DataChip Workspace", "pageTitle")
        ml.addWidget(title)
        info = Ui.label(
            "Create typed DataChip assemblies visually; reconstruct and verify "
            "content through BTDU and ENTITY. Licence, trade, transfer and "
            "deploy only through separately authorized workflows.", "muted")
        info.setWordWrap(True)
        ml.addWidget(info)
        buttons=QtWidgets.QHBoxLayout()
        for label,key in [
            ("Open DataChip Composer","composer"),
            ("Browse controlled assets","assets"),
            ("Rights & instruments","instruments"),
            ("Explore Capability Exchange","market"),
            ("Review Treasury","overview")
        ]:
            b=Ui.button(label,key=="composer")
            b.clicked.connect(lambda checked=False,k=key:self.navigate(k))
            buttons.addWidget(b)
        buttons.addStretch()
        ml.addLayout(buttons)
        lay.addWidget(message)
        panels=QtWidgets.QHBoxLayout()
        lib=QtWidgets.QFrame();lib.setProperty("class","panel")
        ll=QtWidgets.QVBoxLayout(lib)
        ll.addWidget(Ui.label("YOUR LIBRARY & ASSEMBLIES","sectionTitle"))
        self.workspace_summary=QtWidgets.QTextBrowser()
        self.workspace_summary.setProperty("class","detail")
        ll.addWidget(self.workspace_summary)
        panels.addWidget(lib,2)
        rights=QtWidgets.QFrame();rights.setProperty("class","panel")
        rl=QtWidgets.QVBoxLayout(rights)
        rl.addWidget(Ui.label("SECURITY / COMPOSITION BOUNDARY","sectionTitle"))
        explanation=Ui.label(
            "This first Composer compiles deterministic typed graphs only. "
            "An imported chip hash verifies bytes, never ownership or licence. "
            "No untrusted code execution, host deployment, wallet transfer, "
            "grant issuance or exchange settlement is permitted from graph links.", "muted")
        explanation.setWordWrap(True)
        rl.addWidget(explanation);rl.addStretch()
        panels.addWidget(rights,1)
        lay.addLayout(panels,1)
        return p

    def _composer_page(self):
        self.composer_page=COMPOSER_UI.ComposerPage(
            self.state,self.entity_id,self,asset_provider=self.backend.snapshot)
        return self.composer_page

    def _overview_page(self):
        p = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(p); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(14)
        cards = QtWidgets.QHBoxLayout(); cards.setSpacing(12)
        self.cards = {}
        for key, title in [
            ("assets", "Digital Assets"), ("instruments", "Issued Instruments"), ("listings", "Active Listings"),
            ("positions", "Market Positions"), ("settled", "30D Settled Volume"),
        ]:
            c = MetricCard(title); self.cards[key] = c; cards.addWidget(c)
        lay.addLayout(cards)
        row = QtWidgets.QHBoxLayout(); row.setSpacing(14)
        market_box = QtWidgets.QFrame(); market_box.setProperty("class", "panel")
        ml = QtWidgets.QVBoxLayout(market_box); ml.setContentsMargins(18, 16, 18, 18)
        head = QtWidgets.QHBoxLayout()
        head.addWidget(Ui.label("MARKET PULSE", "sectionTitle")); head.addStretch()
        b = Ui.button("Open market"); b.clicked.connect(lambda: self.navigate("market")); head.addWidget(b)
        ml.addLayout(head)
        self.overview_market_stack=QtWidgets.QStackedWidget()
        self.overview_market = Ui.table(["TICKER", "RIGHTS", "LAST", "24H VOL", "30D VOL", "BUYERS", "INTEGRITY"])
        self.overview_market_empty=EmptyState(
            "NO ACTIVE LISTINGS",
            "The universal market is clean. Issue an economic instrument from a controlled DCO, then create a listing to establish a ticker-addressable market."
        )
        self.overview_market_stack.addWidget(self.overview_market)
        self.overview_market_stack.addWidget(self.overview_market_empty)
        ml.addWidget(self.overview_market_stack, 1)
        row.addWidget(market_box, 2)

        asset_box = QtWidgets.QFrame(); asset_box.setProperty("class", "panel")
        al = QtWidgets.QVBoxLayout(asset_box); al.setContentsMargins(18, 16, 18, 18)
        ah = QtWidgets.QHBoxLayout(); ah.addWidget(Ui.label("ASSET PORTFOLIO", "sectionTitle")); ah.addStretch()
        ab = Ui.button("+ Ingest asset", True); ab.clicked.connect(self.ingest_asset); ah.addWidget(ab); al.addLayout(ah)
        self.overview_assets = Ui.table(["TICKER", "ASSET", "CLASS", "DOMAIN", "ASSET INFO"])
        self.overview_assets.setColumnWidth(0,150)
        self.overview_assets.setColumnWidth(1,310)
        self.overview_assets.setColumnWidth(2,170)
        self.overview_assets.horizontalHeader().setSectionResizeMode(1,QtWidgets.QHeaderView.Stretch)
        al.addWidget(self.overview_assets, 1)
        row.addWidget(asset_box, 3)
        lay.addLayout(row, 1)

        boundary = QtWidgets.QFrame(); boundary.setProperty("class", "notice")
        nl = QtWidgets.QHBoxLayout(boundary); nl.setContentsMargins(16, 12, 16, 12)
        nl.addWidget(Ui.label("VALUE BOUNDARY", "eyebrow"))
        n = Ui.label("ENTITY measures market demand for bounded rights. A rights price is not intrinsic DCO value and is not accounting fair value.", "muted")
        n.setWordWrap(True); nl.addWidget(n, 1)
        lay.addWidget(boundary)
        return p

    def _assets_page(self):
        p = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(p); lay.setContentsMargins(0,0,0,0); lay.setSpacing(12)
        actions = QtWidgets.QHBoxLayout()
        ingest = Ui.button("+ Ingest digital asset", True); ingest.clicked.connect(self.ingest_asset)
        formula_store = Ui.button("Add to Formula Storage"); formula_store.clicked.connect(self.add_selected_asset_to_formula_storage)
        activate_transfer = Ui.button("Activate Transferred Asset"); activate_transfer.clicked.connect(self.activate_selected_transferred_asset)
        export_asset = Ui.button("Export / Reconstruct asset"); export_asset.clicked.connect(self.export_selected_asset)
        disclose = Ui.button("Asset information"); disclose.clicked.connect(self.edit_asset_information)
        issue = Ui.button("Issue economic instrument"); issue.clicked.connect(self.issue_selected_asset)
        lineage = Ui.button("Inspect lineage"); lineage.clicked.connect(self.show_asset_lineage)
        actions.addWidget(ingest); actions.addWidget(formula_store); actions.addWidget(activate_transfer); actions.addWidget(export_asset); actions.addWidget(disclose); actions.addWidget(issue); actions.addWidget(lineage); actions.addStretch()
        lay.addLayout(actions)
        split = QtWidgets.QSplitter()
        self.assets_table = Ui.table(["TICKER(S)", "ASSET", "CLASS", "TYPE", "DOMAIN", "ASSET INFO", "PASSPORT", "BTDU", "DCO ID"])
        self.assets_table.itemSelectionChanged.connect(self.update_asset_detail)
        split.addWidget(self.assets_table)
        self.asset_detail = QtWidgets.QTextBrowser(); self.asset_detail.setProperty("class", "detail")
        split.addWidget(self.asset_detail); split.setSizes([1050, 410])
        lay.addWidget(split, 1)
        return p

    def _instruments_page(self):
        p = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(p); lay.setContentsMargins(0,0,0,0); lay.setSpacing(12)
        actions = QtWidgets.QHBoxLayout()
        list_btn = Ui.button("+ Create listing", True); list_btn.clicked.connect(self.list_selected_instrument)
        actions.addWidget(list_btn); actions.addStretch()
        lay.addLayout(actions)
        split = QtWidgets.QSplitter()
        self.instruments_table = Ui.table(["TICKER", "INSTRUMENT", "RIGHTS", "CLASS", "SUPPLY", "DCO", "STATUS"])
        self.instruments_table.itemSelectionChanged.connect(self.update_instrument_detail)
        split.addWidget(self.instruments_table)
        self.instrument_detail = QtWidgets.QTextBrowser(); self.instrument_detail.setProperty("class", "detail")
        split.addWidget(self.instrument_detail); split.setSizes([1050, 410])
        lay.addWidget(split, 1)
        return p

    def _market_page(self):
        p = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(p); lay.setContentsMargins(0,0,0,0); lay.setSpacing(12)
        actions = QtWidgets.QHBoxLayout()
        buy = Ui.button("BUY", True); buy.clicked.connect(lambda: self.trade_selected("BUY"))
        sell = Ui.button("SELL"); sell.clicked.connect(lambda: self.trade_selected("SELL"))
        info = Ui.button("Listing information"); info.clicked.connect(self.show_listing_info)
        export = Ui.button("Export instrument package"); export.clicked.connect(self.export_listing)
        actions.addWidget(buy); actions.addWidget(sell); actions.addWidget(info); actions.addWidget(export); actions.addStretch()
        lay.addLayout(actions)
        split = QtWidgets.QSplitter()
        self.market_table = Ui.table(["TICKER", "INSTRUMENT", "ISSUER", "RIGHTS", "LAST", "BID", "ASK", "24H VOL", "30D VOL", "BUYERS", "HOLDERS", "INTEGRITY"])
        self.market_table.itemSelectionChanged.connect(self.update_market_detail)
        split.addWidget(self.market_table)
        self.market_detail = QtWidgets.QTextBrowser(); self.market_detail.setProperty("class", "detail")
        split.addWidget(self.market_detail); split.setSizes([1110, 350])
        lay.addWidget(split, 1)
        return p

    def _intelligence_page(self):
        p = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(p); lay.setContentsMargins(0,0,0,0); lay.setSpacing(12)
        notice = EmptyState("DATA VALUE DISCOVERY", "Settled market activity reveals which bounded rights attract demand. Orders and quotes do not count as realized demand; self-trades and reciprocal flows are flagged.")
        lay.addWidget(notice)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        top = QtWidgets.QFrame(); top.setProperty("class", "panel"); tl = QtWidgets.QVBoxLayout(top)
        tl.addWidget(Ui.label("INSTRUMENT RIGHTS DEMAND", "sectionTitle"))
        self.intel_table = Ui.table(["TICKER", "RIGHTS", "ASSET CLASS", "LAST", "24H UNITS", "30D UNITS", "30D TRADES", "BUYERS", "HOLDERS", "LOW", "HIGH", "VERIFIED", "INTEGRITY"])
        tl.addWidget(self.intel_table)
        splitter.addWidget(top)
        bottom = QtWidgets.QFrame(); bottom.setProperty("class", "panel"); bl = QtWidgets.QVBoxLayout(bottom)
        bl.addWidget(Ui.label("ASSET-CLASS ROLLUP · 30 DAYS", "sectionTitle"))
        self.rollup_table = Ui.table(["ASSET CLASS", "INSTRUMENTS", "TRADES", "UNITS", "NOTIONAL BY CURRENCY"])
        bl.addWidget(self.rollup_table); splitter.addWidget(bottom)
        splitter.setSizes([430, 280]); lay.addWidget(splitter, 1)
        return p

    def _orders_page(self):
        p = QtWidgets.QWidget(); lay = QtWidgets.QVBoxLayout(p); lay.setContentsMargins(0,0,0,0); lay.setSpacing(12)
        settle_box = QtWidgets.QFrame(); settle_box.setProperty("class", "panel")
        sl = QtWidgets.QVBoxLayout(settle_box)
        sh = QtWidgets.QHBoxLayout()
        sh.addWidget(Ui.label("PENDING SETTLEMENT / DELIVERY", "sectionTitle")); sh.addStretch()
        complete = Ui.button("Complete Settlement / Deliver", True)
        complete.clicked.connect(self.complete_selected_settlement)
        sh.addWidget(complete); sl.addLayout(sh)
        self.settlements_table = Ui.table([
            "TRADE", "INSTRUMENT", "ROLE", "QTY", "AMOUNT", "CURRENCY", "DELIVERY", "STATUS"
        ])
        sl.addWidget(self.settlements_table)
        lay.addWidget(settle_box, 1)
        box = QtWidgets.QFrame(); box.setProperty("class", "panel"); bl = QtWidgets.QVBoxLayout(box)
        bl.addWidget(Ui.label("OPEN / RECENT ORDERS", "sectionTitle"))
        self.orders_table = Ui.table(["TICKER / INSTRUMENT", "SIDE", "REMAINING", "LIMIT", "STATUS"])
        bl.addWidget(self.orders_table); lay.addWidget(box, 1)
        return p

    def navigate(self, key):
        idx = list(self.pages).index(key)
        self.stack.setCurrentIndex(idx)
        for k, b in self.nav_buttons.items():
            b.setChecked(k == key)
        titles = {
            "workspace": ("ENTITY Workspace", "Composable verified content, native hosts and rights-controlled exchange."),
            "composer": ("DataChip Composer", "Drag, connect, validate and save typed DataChip graph assemblies."),
            "overview": ("Treasury & Market Overview", "Legacy economics, asset portfolio and settlement overview."),
            "assets": ("DataChip Library & Digital Assets", "Existing DCOs, BTDU formula storage, ownership lineage, and asset ingestion."),
            "instruments": ("Rights Instruments", "Optional licences and bounded economic instruments issued against controlled assets."),
            "market": ("Capability Exchange", "Existing multi-issuer bounded-rights listings and wallet-to-wallet settlement."),
            "intelligence": ("Economic Intelligence", "Settlement-aware price discovery and rights-demand analytics."),
            "orders": ("Orders", "Open and recent exchange instructions."),
        }
        self.page_title.setText(titles[key][0]); self.page_sub.setText(titles[key][1])

    def refresh(self):
        self.snapshot_data = self.backend.snapshot()
        self.assets_rows = self.snapshot_data.get("assets", [])
        drafts = self.composer_page.store.list_drafts()
        self.workspace_summary.setHtml(
            "<h2>Controlled DCO assets: "+str(len(self.assets_rows))+"</h2>"
            "<p>Local DataChip assembly drafts: <b>"+str(len(drafts))+"</b></p>"
            "<p>Verified formula storage and Rights Passports remain managed by their "
            "existing authoritative ENTITY modules; this workspace does not "
            "create ownership or execute modules.</p>"
            "<p>Use the Composer to create a plan, or open the Library to inspect "
            "existing assets and reconstructive storage.</p>"
        )
        self.instruments_rows = self.backend.instruments()
        self.market_rows = self.backend.market()
        self.metrics_rows = self.backend.economic_metrics()
        self.settlements_rows = self.backend.pending_settlements()
        rollup = self.backend.economy_rollup("asset_class")
        amap = self.backend.instrument_map_by_asset()
        ns_info=self.backend.namespace_info()
        ns=ns_info.get("namespace") or "UNASSIGNED"
        venues = self.backend.venues()

        name = self.backend.identity_manifest.get("display_name") or self.entity_id
        public_aliases = [str(x) for x in (self.backend.identity_manifest.get("aliases") or []) if str(x).endswith(".entity")]
        active_public = public_aliases[0] if public_aliases else shorten(self.entity_id, 12, 8)
        self.identity_chip.setText(f"{name}\n{active_public}")
        if self.wallet_profile:
            self.lineage_chip.setText("LINEAGE  " + self.wallet_profile.get("display_path", active_public))
            self.lineage_chip.setToolTip(
                "User/organization lineage for this wallet. This is separate from ENTITY protocol origin."
            )
        else:
            self.lineage_chip.setText("LINEAGE  " + active_public)
        self.namespace_chip.setText(f"NAMESPACE  {ns}" + ("" if ns_info.get("registered") else "  ·  RESERVED ON ISSUE"))
        self.market_chip.setText(f"ENTITY-MKT  ·  {len(venues)} VENUE{'S' if len(venues)!=1 else ''}")
        if self.market_rows:
            tape = "    ".join(
                f"{r['market_identifier']}  {r['market'].get('last') if r['market'].get('last') is not None else '—'}"
                for r in self.market_rows[:8]
            )
            self.tape.setText("MARKET TAPE    " + tape)
        else:
            self.tape.setText("MARKET TAPE    NO ACTIVE LISTINGS · instruments remain private until explicitly listed")

        self.cards["assets"].value.setText(str(len(self.assets_rows)))
        self.cards["assets"].note.setText("Current DCO holdings")
        self.cards["instruments"].value.setText(str(len(self.instruments_rows)))
        self.cards["instruments"].note.setText("Canonical economic instruments")
        self.cards["listings"].value.setText(str(len(self.market_rows)))
        self.cards["listings"].note.setText("Visible market listings")
        self.cards["positions"].value.setText(str(len(self.snapshot_data.get("positions", []))))
        self.cards["positions"].note.setText("Active rights positions")
        by_currency = {}
        for m in self.metrics_rows:
            cur = m.get("settlement_currency") or "?"
            by_currency[cur] = by_currency.get(cur, 0) + int(m["window_30d"]["notional_amount_units"])
        self.cards["settled"].value.setText(" · ".join(f"{k} {v:,}" for k,v in by_currency.items()) or "—")
        self.cards["settled"].note.setText("Settled instrument-right notional")

        asset_table_rows = []
        overview_assets = []
        for a in self.assets_rows:
            instruments = amap.get(a["object_id"], [])
            tickers = ", ".join(i["market_identifier"] for i in instruments) or "NO TICKER"
            lin = a.get("lineage", {})
            domain = (lin.get("protocol_lineage", {}) or {}).get("primary_domain_profile") or "—"
            gp = lin.get("global_passport") or {}
            btdu_info = (lin.get("capability_bindings", {}).get("BTDU", {}) or {})
            btdu = btdu_info.get("bound", False)
            formula_set = self.backend.formula_storage_status(a["object_id"])
            if formula_set:
                btdu_status = f"FORMULA SET · {formula_set['item_count']} FILE" + ("" if formula_set["item_count"] == 1 else "S")
            else:
                bref = str((btdu_info.get("binding") or {}).get("object_ref") or "")
                btdu_status = "BOUND COMPONENT" if bref.startswith("btdu-object:") else ("LEGACY REF" if btdu else "—")
            disclosure = self.backend.asset_disclosure(a["object_id"])
            disclosure_status = f"SIGNED V{disclosure['version']}" if disclosure else "REQUIRED TO LIST"
            asset_table_rows.append([
                tickers, a.get("title"), a.get("commodity_class"), a.get("object_type"), domain,
                disclosure_status, gp.get("version") or "—", btdu_status, a.get("object_id")
            ])
            overview_assets.append([tickers, a.get("title"), a.get("commodity_class"), domain, disclosure_status])
        Ui.fill_table(self.assets_table, asset_table_rows)
        Ui.fill_table(self.overview_assets, overview_assets[:8])

        inst_rows = []
        for x in self.instruments_rows:
            inst_rows.append([
                x["market_identifier"], x["instrument_name"], x["rights_class"], x["instrument_class"],
                x["supply"], shorten(x["underlying_dco_id"], 12, 8), x["status"]
            ])
        Ui.fill_table(self.instruments_table, inst_rows)

        metrics_by_iid = {m["instrument_id"]: m for m in self.metrics_rows}
        market_rows = []
        overview_market = []
        for r in self.market_rows:
            mkt = r["market"]; im = metrics_by_iid.get(r["instrument_id"], {})
            w24 = im.get("window_24h", {}); w30 = im.get("window_30d", {})
            flags = ", ".join((im.get("market_integrity") or {}).get("flags") or []) or "CLEAN"
            vals = [
                r["market_identifier"], r["instrument_name"], shorten(r["issuer_entity_id"], 12, 8),
                r["rights_class"], mkt.get("last") or "—", mkt.get("bid") or "—", mkt.get("ask") or "—",
                w24.get("volume_units", 0), w30.get("volume_units", 0), w30.get("unique_buyers", 0),
                im.get("active_holder_count", 0), flags
            ]
            market_rows.append(vals)
            overview_market.append([r["market_identifier"], r["rights_class"], mkt.get("last") or "—",
                                    w24.get("volume_units", 0), w30.get("volume_units", 0),
                                    w30.get("unique_buyers", 0), flags])
        Ui.fill_table(self.market_table, market_rows)
        Ui.fill_table(self.overview_market, overview_market[:8])
        self.overview_market_stack.setCurrentIndex(0 if overview_market else 1)

        intel_rows = []
        for m in self.metrics_rows:
            w = m["window_30d"]
            flags = ", ".join(m["market_integrity"]["flags"]) or "CLEAN"
            intel_rows.append([
                m["market_identifier"], m["rights_class"], m["asset_class"], m["last_settled_price"] or "—",
                m["window_24h"]["volume_units"], w["volume_units"], w["trade_count"], w["unique_buyers"],
                m["active_holder_count"], w["low_price"] or "—", w["high_price"] or "—",
                w["externally_verified_trade_count"], flags
            ])
        Ui.fill_table(self.intel_table, intel_rows)
        Ui.fill_table(self.rollup_table, [
            [r["group"], r["instrument_count"], r["settled_trades_30d"], r["volume_units_30d"],
             ", ".join(f"{k} {v:,}" for k,v in r["notional_30d_by_currency"].items()) or "—"]
            for r in rollup.get("rows", [])
        ])

        Ui.fill_table(self.settlements_table, [
            [
                shorten(s["trade_id"], 13, 8),
                s.get("market_identifier") or shorten(s["instrument_id"], 14, 8),
                s["role"], s["quantity"], s["amount_units"], s["currency"],
                s["delivery_kind"], s["status"],
            ]
            for s in self.settlements_rows
        ])
        Ui.fill_table(self.orders_table, [
            [o["instrument_id"], o["side"], o["remaining"], o["limit_price"], o["status"]]
            for o in self.snapshot_data.get("orders", [])
        ])
        if self.assets_rows:
            self.assets_table.selectRow(0)
        if self.instruments_rows:
            self.instruments_table.selectRow(0)
        if self.market_rows:
            self.market_table.selectRow(0)

    def selected_asset(self):
        row = self.assets_table.currentRow()
        return self.assets_rows[row] if 0 <= row < len(self.assets_rows) else None

    def selected_settlement(self):
        row = self.settlements_table.currentRow()
        return self.settlements_rows[row] if 0 <= row < len(self.settlements_rows) else None

    def selected_instrument(self):
        row = self.instruments_table.currentRow()
        return self.instruments_rows[row] if 0 <= row < len(self.instruments_rows) else None

    def selected_market(self):
        row = self.market_table.currentRow()
        return self.market_rows[row] if 0 <= row < len(self.market_rows) else None

    def update_asset_detail(self):
        a = self.selected_asset()
        if not a:
            self.asset_detail.setHtml("<h2>No asset selected</h2>"); return
        lin = a.get("lineage", {}); p = lin.get("protocol_lineage", {}) or {}
        al = lin.get("asset_lineage", {}) or {}; cap = lin.get("capability_bindings", {}) or {}
        instruments = self.backend.instrument_map_by_asset().get(a["object_id"], [])
        tickers = "<br>".join(html.escape(i["market_identifier"]) for i in instruments) or "<span>NO ECONOMIC INSTRUMENT ISSUED</span>"
        parents = "<br>".join(
            f"{html.escape(str(x.get('relation') or ''))} · {html.escape(str(x.get('title') or shorten(x.get('parent_object_id'))))}"
            for x in al.get("parents", [])
        ) or "None recorded"
        obj = self.backend.asset_record(a["object_id"])
        descriptor = obj.get("descriptor") or {}
        metadata = descriptor.get("metadata") or {}
        disclosure = self.backend.asset_disclosure(a["object_id"])
        try:
            gp = self.backend.latest_global_passport(a["object_id"])
        except Exception:
            gp = {}
        description = (disclosure or {}).get("description") or (
            f"{obj.get('title')} is registered as an ENTITY Digital Commodity Object of type "
            f"{obj.get('object_type')} in the {descriptor.get('commodity_class')} commodity class. "
            "No signed issuer-authored Asset Disclosure has been published yet."
        )
        def ul(items):
            vals=[html.escape(str(x)) for x in (items or []) if str(x).strip()]
            return "<ul>"+"".join("<li>"+x+"</li>" for x in vals)+"</ul>" if vals else "<span>None stated</span>"
        metadata_rows = "".join(
            f"<tr><td>{html.escape(str(k).replace('_',' ').title())}</td><td>{html.escape(str(v))}</td></tr>"
            for k,v in sorted(metadata.items())
        ) or "<tr><td colspan='2'>None recorded</td></tr>"
        disclosure_version=(disclosure or {}).get("version")
        profile_refs=(gp.get("profile_stack") or {}).get("profile_refs") or []
        self.asset_detail.setHtml(f"""
        <div class='eyebrow'>DIGITAL COMMODITY OBJECT</div>
        <h1>{html.escape(str(a.get('title') or ''))}</h1>
        <div class='ticker'>{tickers}</div>
        <hr>
        <h3>Asset description</h3>
        <p>{html.escape(str(description))}</p>
        <p><b>Disclosure:</b> {"Signed version "+str(disclosure_version) if disclosure else "Not yet published"}</p>

        <h3>Canonical identity</h3>
        <b>Canonical lineage</b><br>{html.escape(str(p.get('display_path') or 'Unresolved'))}<br><br>
        <b>Controller</b><br>{html.escape(str(al.get('controller_name') or a.get('controller_entity_id')))}<br><br>
        <b>DCO ID</b><br><code>{html.escape(str(a.get('object_id')))}</code><br><br>
        <b>Commodity class</b><br>{html.escape(str(a.get('commodity_class')))}<br><br>
        <b>Object type</b><br>{html.escape(str(a.get('object_type')))}<br><br>
        <b>Content SHA-256</b><br><code>{html.escape(str(obj.get('content_sha256') or '—'))}</code><br><br>

        <h3>Issuer disclosure</h3>
        <b>Purpose</b><br>{html.escape(str((disclosure or {}).get('purpose') or 'None stated'))}<br><br>
        <b>Capabilities</b>{ul((disclosure or {}).get('capabilities'))}
        <b>Included content / components</b>{ul((disclosure or {}).get('contents'))}
        <b>Intended uses</b>{ul((disclosure or {}).get('intended_uses'))}
        <b>Limitations</b>{ul((disclosure or {}).get('limitations'))}
        <b>Validation notes</b>{ul((disclosure or {}).get('validation_notes'))}

        <h3>Technical metadata</h3>
        <table cellspacing='0' cellpadding='4'>{metadata_rows}</table><br>
        <b>Profile stack</b>{ul(profile_refs)}
        <b>Composed profiles</b><br>{html.escape(', '.join(p.get('composed_domain_profiles') or []) or 'Primary domain only')}<br><br>
        <b>BTDU</b><br>{html.escape(
            (lambda fs: f"FORMULA SET · {fs['item_count']} FILE" + ("" if fs['item_count'] == 1 else "S") + f" · {fs['logical_bytes']:,} BYTES"
             if fs else ("BOUND COMPONENT / LEGACY PASSPORT BINDING" if (cap.get('BTDU') or {}).get('bound') else "Not bound"))
            (self.backend.formula_storage_status(a["object_id"]))
        )}<br><br>
        <b>Transfer passport activation</b><br>{html.escape(
            (lambda s: "BUYER PASSPORT ACTIVATION REQUIRED" if s.get("required") else ("ACTIVE" if s.get("active") else str(s.get("reason") or "—")))
            (self.backend.transfer_activation_status(a["object_id"]))
        )}<br><br>
        <b>Provenance parents</b><br>{parents}<br><br>
        <small>Asset registration does not create a ticker, instrument, listing or market value. A signed Asset Disclosure is required before market listing.</small>
        """)


    def update_instrument_detail(self):
        x = self.selected_instrument()
        if not x:
            self.instrument_detail.setHtml("<h2>No instrument selected</h2>"); return
        self.instrument_detail.setHtml(f"""
        <div class='eyebrow'>CANONICAL ECONOMIC INSTRUMENT</div>
        <div class='ticker'>{x['market_identifier']}</div>
        <h1>{x['instrument_name']}</h1><hr>
        <b>Canonical instrument ID</b><br><code>{x['instrument_id']}</code><br><br>
        <b>Underlying DCO</b><br><code>{x['underlying_dco_id']}</code><br><br>
        <b>Rights class</b><br>{x['rights_class']}<br><br>
        <b>Instrument class</b><br>{x['instrument_class']}<br><br>
        <b>Supply</b><br>{x['supply']:,}<br><br>
        <b>Fungibility</b><br>{x['fungibility']}<br><br>
        <b>Jurisdiction</b><br>{x['jurisdiction']}<br><br>
        <b>Rights Passport</b><br><code>{x['rights_passport_id']}</code><br><br>
        <small>The ticker is a human market alias. The canonical instrument ID remains authoritative.</small>
        """)

    def update_market_detail(self):
        r = self.selected_market()
        if not r:
            self.market_detail.setHtml("<h2>No active listing</h2><p>Assets remain private until an issuer explicitly creates an instrument and listing.</p>")
            return
        m = r["market"]
        im = next((x for x in self.metrics_rows if x["instrument_id"] == r["instrument_id"]), {})
        w = im.get("window_30d", {})
        flags = ", ".join((im.get("market_integrity") or {}).get("flags") or []) or "CLEAN"
        self.market_detail.setHtml(f"""
        <div class='eyebrow'>ENTITY MARKET</div>
        <div class='ticker'>{r['market_identifier']}</div>
        <h1>{r['instrument_name']}</h1><hr>
        <table>
        <tr><td>LAST</td><td><b>{m.get('last') or '—'}</b></td></tr>
        <tr><td>BID</td><td>{m.get('bid') or '—'}</td></tr>
        <tr><td>ASK</td><td>{m.get('ask') or '—'}</td></tr>
        <tr><td>30D UNITS</td><td>{w.get('volume_units', 0):,}</td></tr>
        <tr><td>30D TRADES</td><td>{w.get('trade_count', 0):,}</td></tr>
        <tr><td>BUYERS</td><td>{w.get('unique_buyers', 0):,}</td></tr>
        <tr><td>HOLDERS</td><td>{im.get('active_holder_count', 0):,}</td></tr>
        </table><br>
        <b>Rights</b><br>{r['rights_class']}<br><br>
        <b>Issuer</b><br><code>{r['issuer_entity_id']}</code><br><br>
        <b>Integrity</b><br>{flags}<br><br>
        <small>Observed price describes this instrument's bounded rights under its terms—not intrinsic DCO value.</small>
        """)

    def ingest_asset(self):
        path = QtWidgets.QFileDialog.getOpenFileName(self, "Choose digital asset to ingest")[0]
        if not path:
            return
        d = AssetIngestDialog(self, Path(path), self.backend)
        if d.exec() != QtWidgets.QDialog.Accepted:
            return
        try:
            result = self.backend.ingest(path, d.result_data)
            self.refresh()
            QtWidgets.QMessageBox.information(
                self, "Digital asset registered",
                f"DCO\n{result['digital_asset']['object_id']}\n\n"
                f"Global Passport verified: {result['global_passport_verified']}\n"
                f"BTDU bound: {bool(result['btdu_binding'])}\n\n"
                "No economic instrument, ticker, listing or price was created."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Asset ingest failed", str(e))

    def activate_selected_transferred_asset(self):
        asset = self.selected_asset()
        if not asset:
            QtWidgets.QMessageBox.warning(self, "Transferred Asset", "Select a transferred digital asset first.")
            return
        try:
            status = self.backend.transfer_activation_status(asset["object_id"])
            if not status.get("controlled_by_wallet"):
                QtWidgets.QMessageBox.warning(
                    self, "Transferred Asset",
                    "The active wallet is not the current controller of this DCO."
                )
                return
            if not status.get("required"):
                QtWidgets.QMessageBox.information(
                    self, "Transferred Asset",
                    "This DCO already has an active Rights Passport and Global Passport signed by this wallet."
                )
                return
            answer = QtWidgets.QMessageBox.question(
                self, "Activate Transferred Asset",
                "Create new buyer-controlled Rights and Global Passports using this wallet's own signing key?\n\n"
                "The historical seller passports remain immutable. The new Rights Passport grants only CONTROL "
                "and TRANSFER authority from the settled sale; it does not silently inherit copyright, patent, "
                "commercialisation, training or derivative rights.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes,
            )
            if answer != QtWidgets.QMessageBox.Yes:
                return
            result = self.backend.activate_transferred_asset(asset["object_id"])
            self.refresh()
            self.update_asset_detail()
            QtWidgets.QMessageBox.information(
                self, "Transferred Asset Activated",
                f"{asset.get('title')}\n\n"
                f"Controller\n{result['controller_entity_id']}\n\n"
                f"Rights Passport\n{result['rights_passport_id']}\n\n"
                f"Global Passport\n{result['global_passport_id']}\n\n"
                "The buyer can now manage or relist the DCO under its own controller identity. "
                "Historical seller passports were preserved."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Transfer activation failed", str(e))

    def add_selected_asset_to_formula_storage(self):
        asset = self.selected_asset()
        if not asset:
            QtWidgets.QMessageBox.warning(self, "Formula Storage", "Select an existing digital asset first.")
            return

        picker = QtWidgets.QMessageBox(self)
        picker.setWindowTitle("Add to Formula Storage")
        picker.setIcon(QtWidgets.QMessageBox.Information)
        picker.setText("Choose what should become reconstructive BTDU formula storage for this existing asset.")
        picker.setInformativeText(
            "File stores one file. Folder stores every regular file recursively and preserves the folder tree. "
            "Original files are not deleted."
        )
        file_btn = picker.addButton("Choose File", QtWidgets.QMessageBox.ActionRole)
        folder_btn = picker.addButton("Choose Folder", QtWidgets.QMessageBox.ActionRole)
        picker.addButton(QtWidgets.QMessageBox.Cancel)
        picker.exec()
        clicked = picker.clickedButton()
        if clicked is file_btn:
            source = QtWidgets.QFileDialog.getOpenFileName(self, "Choose file to add to formula storage")[0]
        elif clicked is folder_btn:
            source = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose folder to add to formula storage")
        else:
            return
        if not source:
            return

        progress = QtWidgets.QProgressDialog("Preparing formula storage…", None, 0, 0, self)
        progress.setWindowTitle("BTDU Formula Storage")
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)
        progress.show()

        def update_progress(index, total, rel):
            if progress.maximum() != total:
                progress.setRange(0, total)
            progress.setValue(index - 1)
            progress.setLabelText(f"Formulating {index} / {total}\\n{rel}")
            QtWidgets.QApplication.processEvents()

        try:
            result = self.backend.add_asset_to_formula_storage(asset["object_id"], source, update_progress)
            progress.setValue(result["item_count"])
            self.refresh()
            self.update_asset_detail()
            QtWidgets.QMessageBox.information(
                self, "Formula storage verified",
                f"{asset.get('title')}\\n\\n"
                f"Source: {result['source_kind']}\\n"
                f"Formula files: {result['item_count']:,}\\n"
                f"Logical bytes: {result['logical_bytes']:,}\\n"
                f"Manifest SHA-256: {result['manifest_sha256']}\\n\\n"
                "Every file passed deep reconstructive verification. "
                "The original file/folder was left untouched. "
                "Export / Reconstruct can now rebuild this formula set back onto disk."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Formula storage failed", str(e))
        finally:
            progress.close()

    def export_selected_asset(self):
        asset = self.selected_asset()
        if not asset:
            QtWidgets.QMessageBox.warning(self, "BTDU export", "Select a digital asset first.")
            return

        formula_set = self.backend.formula_storage_status(asset["object_id"])
        if formula_set:
            if formula_set["source_kind"] == "FILE":
                suggested = formula_set["source_name"] or "ENTITY-asset"
                dest = QtWidgets.QFileDialog.getSaveFileName(
                    self, "Reconstruct formula-stored file to disk", str(Path.home() / suggested)
                )[0]
            else:
                dest = QtWidgets.QFileDialog.getExistingDirectory(
                    self, "Choose destination folder for reconstructed asset"
                )
            if not dest:
                return
            try:
                result = self.backend.export_formula_storage_set(asset["object_id"], dest)
                QtWidgets.QMessageBox.information(
                    self, "Formula-stored asset reconstructed",
                    f"{asset.get('title')}\\n\\n"
                    f"Files reconstructed: {result['item_count']:,}\\n"
                    f"Bytes reconstructed: {result['bytes']:,}\\n"
                    f"Formula-set manifest: {result['manifest_sha256']}\\n\\n"
                    "All reconstructed files were hash-verified. "
                    "The BTDU formula set remains the authoritative stored representation."
                )
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "BTDU export failed", str(e))
            return

        lin = asset.get("lineage", {}) or {}
        btdu = ((lin.get("capability_bindings") or {}).get("BTDU") or {})
        binding = dict(btdu.get("binding") or {})
        object_ref = str(binding.get("object_ref") or "")
        if not btdu.get("bound") or not object_ref:
            QtWidgets.QMessageBox.warning(
                self, "BTDU export",
                "This asset is not yet in reconstructive formula storage. "
                "Use 'Add to Formula Storage' and choose the existing file or folder first."
            )
            return
        if not object_ref.startswith("btdu-object:"):
            QtWidgets.QMessageBox.warning(
                self, "BTDU export",
                "This asset has a legacy/deferred BTDU reference. "
                "Use 'Add to Formula Storage' and choose its existing file or folder to upgrade it."
            )
            return
        try:
            obj = self.backend.asset_record(asset["object_id"])
            descriptor = obj.get("descriptor") or {}
            logical = str(descriptor.get("logical_path") or "").strip()
            suggested = Path(logical).name if logical else str(asset.get("title") or "ENTITY-asset")
            for ch in '<>:"/\\|?*':
                suggested = suggested.replace(ch, "_")
            suggested = suggested.strip(" .") or "ENTITY-asset"
            dest = QtWidgets.QFileDialog.getSaveFileName(
                self, "Reconstruct BTDU-bound component to disk", str(Path.home() / suggested)
            )[0]
            if not dest:
                return
            result = self.backend.export_asset_to_disk(asset["object_id"], dest)
            QtWidgets.QMessageBox.information(
                self, "BTDU component reconstructed",
                f"Reconstructed and verified from BTDU formula.\\n\\n"
                f"File\\n{result['path']}\\n\\n"
                f"Bytes: {result['bytes']:,}\\n"
                f"SHA-256: {result['sha256']}\\n\\n"
                f"Formula object\\n{result.get('formula_object_id') or '—'}\\n\\n"
                f"Scope: {result.get('export_scope')}\\n\\n"
                + ("This export reconstructs the complete DCO payload. "
                   if result.get("export_scope") == "FULL_DCO_PAYLOAD"
                   else "This is the component currently bound by the historical DCO passport. "
                        "Use 'Add to Formula Storage' with the complete source folder to make the full asset reconstructable. ")
                + "The materialized copy is not authoritative; BTDU formula storage remains authoritative."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "BTDU export failed", str(e))

    def edit_asset_information(self):
        asset = self.selected_asset()
        if not asset:
            QtWidgets.QMessageBox.warning(self, "Asset information", "Select a controlled DCO first.")
            return
        current = self.backend.asset_disclosure(asset["object_id"])
        dialog = AssetDisclosureDialog(self, asset, current)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        try:
            result = self.backend.publish_asset_disclosure(asset["object_id"], dialog.result_data)
            self.refresh()
            self.update_asset_detail()
            QtWidgets.QMessageBox.information(
                self, "Asset information published",
                f"Signed Asset Disclosure version {result['version']} was published.\n\n"
                f"Disclosure ID\n{result['disclosure_id']}\n\n"
                "Future listings will snapshot this disclosure together with the canonical asset dossier."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Asset information failed", str(e))

    def issue_selected_asset(self):
        asset = self.selected_asset()
        if not asset:
            QtWidgets.QMessageBox.warning(self, "Instrument", "Select a controlled DCO first."); return
        try:
            rights_profile = self.backend.instrument_rights_profile(asset["object_id"])
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Rights Passport", str(e))
            return
        if not rights_profile["allowed_actions"]:
            QtWidgets.QMessageBox.warning(
                self, "No issuable rights",
                "This DCO's current Rights Passport contains no ALLOW actions. "
                "No economic instrument can be created until the asset is explicitly authorized."
            )
            return
        dialog_asset = dict(asset)
        try:
            obj = self.backend.asset_record(asset["object_id"])
            metadata = ((obj.get("descriptor") or {}).get("metadata") or {})
            dialog_asset["short_name"] = metadata.get("short_name")
            dialog_asset["dco_code"] = metadata.get("dco_code") or asset.get("dco_id")
            dialog_asset["instrument_plan"] = self.backend.instrument_product_plan(asset["object_id"])
        except Exception:
            dialog_asset["instrument_plan"] = []
        d = InstrumentDialog(self, dialog_asset, self.backend.namespace(), rights_profile)
        if d.exec() != QtWidgets.QDialog.Accepted:
            return
        try:
            result = self.backend.create_instrument(asset["object_id"], d.result_data)
            self.refresh()
            QtWidgets.QMessageBox.information(
                self, "Economic instrument issued",
                f"{result['market_identifier']}\n\nCanonical ID\n{result['instrument_id']}\n\n"
                "The instrument is not listed and no market value was created."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Instrument creation failed", str(e))

    def list_selected_instrument(self):
        instrument = self.selected_instrument()
        if not instrument:
            QtWidgets.QMessageBox.warning(self, "Listing", "Select one of your economic instruments."); return
        if not self.backend.asset_disclosure(instrument["underlying_dco_id"]):
            QtWidgets.QMessageBox.warning(
                self, "Asset information required",
                "This DCO does not yet have a signed Asset Disclosure. Publish detailed Asset Information before creating a market listing."
            )
            return
        d = ListingDialog(self, self.backend, instrument)
        if d.exec() != QtWidgets.QDialog.Accepted:
            return
        try:
            result = self.backend.create_listing(instrument["instrument_id"], d.result_data)
            self.refresh()
            QtWidgets.QMessageBox.information(
                self, "Listing created",
                f"{instrument['market_identifier']}\n\nListing ID\n{result['listing_id']}\n\n"
                "Listing Information Sheet and machine manifest are hash-bound."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Listing creation failed", str(e))

    def show_asset_lineage(self):
        a = self.selected_asset()
        if not a:
            return
        lin = a.get("lineage", {})
        p = lin.get("protocol_lineage", {}) or {}
        al = lin.get("asset_lineage", {}) or {}
        parents = "\n".join(
            f"{x.get('relation')}: {x.get('title') or x.get('parent_object_id')}"
            for x in al.get("parents", [])
        ) or "None"
        QtWidgets.QMessageBox.information(
            self, "ENTITY lineage",
            f"CANONICAL PROTOCOL / DOMAIN LINEAGE\n{p.get('display_path') or 'Unresolved'}\n\n"
            f"ASSET CONTROLLER\n{al.get('controller_name') or al.get('controller_entity_id')}\n\n"
            f"PROVENANCE PARENTS\n{parents}\n\n"
            "ADAM, NIKI and BTDU are capability/evidence bindings and do not create ownership."
        )

    def show_listing_info(self):
        r = self.selected_market()
        if not r:
            QtWidgets.QMessageBox.warning(self, "Listing", "No active market listing selected."); return
        try:
            listing = self.backend.market_registry.listing(r["listing_id"])
            dialog = ListingInformationDialog(
                self, listing["information"]["market_identifier"], listing["information_markdown"]
            )
            dialog.exec()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Listing Information", str(e))


    def export_listing(self):
        r = self.selected_market()
        if not r:
            QtWidgets.QMessageBox.warning(self, "Export", "No active market listing selected."); return
        dest = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose export folder")
        if not dest:
            return
        try:
            instrument = self.backend.market_registry.instrument(r["instrument_id"])
            folder = Path(dest) / (instrument["market_identifier"].replace(":", "-") + ".entity-instrument")
            result = self.backend.market_registry.export_portable_package(r["listing_id"], folder)
            QtWidgets.QMessageBox.information(
                self, "Portable instrument package",
                f"{result['market_identifier']}\n\n{result['destination']}\n\n"
                "Includes PDF, Markdown, JSON manifests/passports, verification and SHA256SUMS."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Export failed", str(e))

    def complete_selected_settlement(self):
        row = self.selected_settlement()
        if not row:
            QtWidgets.QMessageBox.warning(self, "Settlement", "Select a pending settlement first.")
            return
        if row.get("seller") != self.entity_id:
            QtWidgets.QMessageBox.information(
                self, "Settlement",
                "This wallet is the buyer. Delivery is completed by the seller/controller after payment confirmation."
            )
            return
        prompt = (
            "Enter the payment or settlement reference confirming value was received.\n\n"
            + ("This is a WHOLE-ASSET delivery. Completing settlement transfers the underlying DCO "
               "controller and its verified formula-storage association to the buyer."
               if row.get("instrument_class") == "ASSET_TRANSFER"
               else "Completing settlement delivers the purchased rights entitlement to the buyer.")
            + "\n\nThis manual confirmation is recorded as seller-confirmed; it is not an external payment attestation."
        )
        ref, ok = QtWidgets.QInputDialog.getText(self, "Complete Settlement / Deliver", prompt)
        if not ok or not ref.strip():
            return
        if row.get("instrument_class") == "ASSET_TRANSFER":
            answer = QtWidgets.QMessageBox.question(
                self, "Confirm Whole-Asset Transfer",
                f"Transfer the underlying DCO to buyer\n{row['buyer']}\n\nafter settlement reference:\n{ref.strip()}?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if answer != QtWidgets.QMessageBox.Yes:
                return
        try:
            result = self.backend.complete_settlement(row["trade_id"], ref.strip())
            self.refresh()
            QtWidgets.QMessageBox.information(
                self, "Settlement complete",
                f"Trade\n{row['trade_id']}\n\n"
                f"Delivery: {result.get('delivery_status')}\n"
                f"Payment reference: {result.get('payment_ref')}\n"
                f"External payment verification: {result.get('external_payment_verification')}\n\n"
                + (
                    f"Underlying DCO transferred to\n{result['asset_transfer']['to_controller_entity_id']}\n\n"
                    f"Controller transfer receipt\n{result['asset_transfer']['transfer_id']}\n\n"
                    "The DCO now belongs to the buyer's controller identity. The buyer's own wallet must "
                    "activate replacement Rights/Global Passports with its private signing key before relisting."
                    if result.get("asset_transfer") else
                    "The purchased rights entitlement is now held by the buyer."
                )
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Settlement failed", str(e))

    def trade_selected(self, side):
        r = self.selected_market()
        if not r:
            QtWidgets.QMessageBox.warning(self, "Market", "No active market listing selected."); return
        d = OrderDialog(self, r, side)
        if d.exec() != QtWidgets.QDialog.Accepted:
            return
        try:
            qty, price = d.result_data
            result = self.backend.submit_order(r, side, qty, price)
            self.refresh()
            QtWidgets.QMessageBox.information(
                self, "Order submitted",
                f"Order accepted.\nImmediate matches: {len(result['trades'])}\n\n"
                "Matched trades now appear under Orders → Pending Settlement / Delivery. "
                "The seller/controller completes delivery only after settlement/payment confirmation."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Order failed", str(e))

    def _apply_style(self):
        self.setStyleSheet(f"""
        * {{
            font-family: "Segoe UI";
            font-size: 10pt;
            color: {TEXT};
        }}
        QMainWindow, QStackedWidget {{ background: {ROOT_BG}; }}
        QWidget {{ color: {TEXT}; }}
        QLabel {{ background: transparent; }}
        #sidebar {{ background: {SIDEBAR_BG}; border-right: 1px solid {BORDER}; }}
        QLabel[class="brand"] {{ font-size: 26pt; font-weight: 800; letter-spacing: 2px; color: {TEXT}; }}
        QLabel[class="brandSub"] {{ font-size: 8pt; font-weight: 700; letter-spacing: 2px; color: {ACCENT}; }}
        QLabel[class="pageTitle"] {{ font-size: 22pt; font-weight: 700; }}
        QLabel[class="pageSub"], QLabel[class="muted"], QLabel[class="monoMuted"] {{ color: {MUTED}; }}
        QLabel[class="monoMuted"] {{ font-family: Consolas; }}
        QLabel[class="eyebrow"] {{ color: {ACCENT}; font-size: 8pt; font-weight: 700; letter-spacing: 1px; }}
        QLabel[class="sectionTitle"] {{ font-size: 11pt; font-weight: 700; letter-spacing: 1px; }}
        QLabel[class="metric"] {{ font-size: 20pt; font-weight: 750; }}
        QLabel[class="emptyTitle"] {{ font-size: 15pt; font-weight: 700; }}
        QLabel[class="dialogTitle"] {{ font-size: 18pt; font-weight: 700; }}
        QLabel[class="tickerHero"] {{ color: {ACCENT}; font-family: Consolas; font-size: 18pt; font-weight: 700; }}
        QLabel[class="tickerPreview"] {{ background: {SIDEBAR_BG}; border: 1px solid {ACCENT_DARK}; border-radius: 6px; padding: 10px; color: {ACCENT}; font-family: Consolas; font-weight: 700; }}
        QLabel[class="chip"] {{ background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 6px; padding: 7px 11px; color: {MUTED}; font-size: 8pt; font-weight: 700; }}
        QLabel[class="identityChip"] {{ background: {PANEL_BG}; border: 1px solid {BORDER}; border-radius: 6px; padding: 6px 11px; font-size: 8pt; }}
        QLabel[class="tape"] {{ background: {SIDEBAR_BG}; border: 1px solid {BORDER}; padding: 9px 12px; color: {ACCENT}; font-family: Consolas; font-size: 9pt; }}
        QLabel[class="sidebarFoot"] {{ color: {MUTED}; font-size: 8pt; line-height: 1.4; }}
        QFrame[class="panel"], QFrame[class="metricCard"], QFrame[class="empty"] {{
            background: {PANEL_BG}; border: 1px solid {BORDER}; border-radius: 8px;
        }}
        QFrame[class="notice"] {{ background: {PANEL_2}; border: 1px solid {ACCENT_DARK}; border-radius: 7px; }}
        QPushButton {{ background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 6px; padding: 8px 13px; font-weight: 600; }}
        QPushButton:hover {{ border-color: {ACCENT_DARK}; background: #1A2027; }}
        QPushButton[primary="true"] {{ background: {ACCENT}; color: #0C0E11; border-color: {ACCENT}; font-weight: 800; }}
        QPushButton[nav="true"] {{ background: transparent; border: none; text-align: left; padding: 10px 10px; color: {MUTED}; font-size: 9pt; font-weight: 650; }}
        QPushButton[nav="true"]:hover {{ background: {PANEL_BG}; color: {TEXT}; }}
        QPushButton[nav="true"]:checked {{ background: {PANEL_2}; color: {TEXT}; border-left: 3px solid {ACCENT}; }}
        QTableWidget {{ background: {PANEL_BG}; alternate-background-color: {PANEL_BG}; border: 1px solid {BORDER}; border-radius: 7px; selection-background-color: #2A251A; selection-color: {TEXT}; }}
        QHeaderView::section {{ background: {SIDEBAR_BG}; color: {MUTED}; border: none; border-bottom: 1px solid {BORDER}; padding: 9px; font-size: 8pt; font-weight: 700; }}
        QTableWidget::item {{ border-bottom: 1px solid #181D23; padding: 7px; }}
        QTableWidget::item:selected {{ background: #2A251A; color: {TEXT}; }}
        QScrollBar:vertical {{ width: 10px; background: {ROOT_BG}; }}
        QScrollBar::handle:vertical {{ background: #303844; min-height: 30px; border-radius: 4px; }}
        QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {{
            background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 5px; padding: 7px; selection-background-color: {ACCENT_DARK};
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {{ border-color: {ACCENT}; }}
        QComboBox QAbstractItemView {{
            background: {PANEL_2}; color: {TEXT}; border: 1px solid {BORDER};
            selection-background-color: #2A251A; selection-color: {TEXT}; outline: none;
        }}
        QListWidget {{
            background: {PANEL_2}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 6px;
            outline: none; padding: 4px;
        }}
        QListWidget::item {{
            background: {PANEL_2}; color: {TEXT}; padding: 8px 7px; border-bottom: 1px solid #1D232B;
        }}
        QListWidget::item:hover {{ background: #1A2027; color: {TEXT}; }}
        QListWidget::item:selected {{ background: #2A251A; color: {TEXT}; }}
        QDialog {{ background: {ROOT_BG}; }}
        QTextBrowser[class="detail"] {{ background: {PANEL_BG}; border: 1px solid {BORDER}; border-radius: 7px; padding: 14px; }}
        QSplitter::handle {{ background: {ROOT_BG}; width: 8px; height: 8px; }}
        QToolTip {{ background: {PANEL_2}; color: {TEXT}; border: 1px solid {BORDER}; }}
        """)

def self_test(state: Path, entity_id: str, wallet_profile: dict | None = None) -> dict:
    backend = Backend(state, entity_id)
    snap = backend.snapshot()
    registry_status = backend.market_registry.status()
    onboarding = ONBOARDING.EntityWalletOnboarding(state)
    profile = wallet_profile or onboarding.profile_for_entity(entity_id)
    auth = onboarding.authenticate(profile) if profile else {"authenticated": False, "reason": "legacy_unprofiled_identity"}
    return {
        "ready": True, "ui_engine": "PySide6", "design": "ENTITY_DATA_ECONOMY_TERMINAL",
        "entity_id": entity_id, "assets": len(snap.get("assets", [])),
        "instruments": len(backend.instruments()), "positions": len(snap.get("positions", [])),
        "orders": len(snap.get("orders", [])), "venues": len(backend.venues()),
        "market_listings": len(backend.market()), "economic_demand_series": len(backend.economic_metrics()),
        "issuer_namespace": backend.namespace(),
        "asset_disclosures": registry_status["counts"].get("asset_disclosures", 0),
        "market_registry_version": registry_status["version"],
        "signed_asset_disclosure_required_for_listing": registry_status.get("signed_asset_disclosure_required_for_listing", False),
        "wallet_profile_id": profile.get("profile_id") if profile else None,
        "wallet_lineage": profile.get("display_path") if profile else None,
        "device_bound_login": bool(auth.get("authenticated")) if profile else False,
        "login_mode": (profile.get("login_policy") or {}).get("mode") if profile else None,
        "public_name_is_alias_not_authority": True,
        "device_information_creates_user_identity": False,
        "protocol_origin_is_separate_from_user_lineage": True,
        "formula_storage_upgrade_supported": True,
        "formula_storage_file_and_folder_supported": True,
        "formula_storage_export_supported": True,
        "asset_transfer_instrument_supported": True,
        "controller_transfer_ledger_supported": True,
        "settlement_delivery_supported": True,
        "buyer_passport_activation_supported": True,
        "formula_storage_sets": (lambda p: (
            0 if not p.exists() else sqlite3.connect(p).execute("SELECT count(*) FROM asset_formula_sets").fetchone()[0]
        ))(state / "wallet" / "btdu_asset_formula_sets.sqlite"),
        "protocol_tax_bps": 0, "cryptocurrency_required": False,
    }

def main():
    ap = argparse.ArgumentParser(description="ENTITY Data Economy Terminal")
    ap.add_argument("--state"); ap.add_argument("--entity")
    ap.add_argument("--self-test", action="store_true"); ap.add_argument("--self-test-output")
    ap.add_argument("--render-preview")
    args = ap.parse_args()
    state = Path(args.state) if args.state else default_state()
    onboarding = ONBOARDING.EntityWalletOnboarding(state)

    wallet_profile = None
    if args.entity:
        wallet_profile = onboarding.profile_for_entity(args.entity)
    else:
        wallet_profile = onboarding.active_profile()
        if wallet_profile:
            args.entity = wallet_profile["active_entity_id"]

    if args.self_test:
        if not args.entity:
            ms = manifests(state)
            if not ms:
                raise SystemExit("No ENTITY identity or wallet profile found")
            args.entity = ms[0]["entity_id"]
        report = self_test(state, args.entity, wallet_profile)
        raw = json.dumps(report, indent=2, sort_keys=True)
        if args.self_test_output:
            Path(args.self_test_output).write_text(raw + "\n", encoding="utf-8")
        else:
            print(raw)
        return

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(startup_stylesheet())

    if not args.entity:
        setup = EntitySetupDialog(None, onboarding)
        if setup.exec() != QtWidgets.QDialog.Accepted or not setup.profile:
            return
        wallet_profile = setup.profile
        args.entity = wallet_profile["active_entity_id"]
    elif wallet_profile is None and not args.render_preview:
        # A legacy explicit --entity remains supported for managed deployments.
        pass
    elif wallet_profile is not None and not args.render_preview:
        login = EntityLoginDialog(None, onboarding)
        if login.exec() != QtWidgets.QDialog.Accepted:
            return
        if login.create_new:
            setup = EntitySetupDialog(None, onboarding)
            if setup.exec() != QtWidgets.QDialog.Accepted or not setup.profile:
                return
            wallet_profile = setup.profile
        else:
            wallet_profile = login.profile
        args.entity = wallet_profile["active_entity_id"]

    window = WalletWindow(state, args.entity, wallet_profile)
    window.show()
    if args.render_preview:
        app.processEvents()
        QtCore.QTimer.singleShot(300, lambda: (
            window.grab().save(str(Path(args.render_preview))),
            app.quit()
        ))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
