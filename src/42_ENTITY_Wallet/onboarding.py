from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import importlib.util
import json
import os
import platform
import secrets
import socket
import sqlite3
import sys
import time
import uuid

SCHEMA = "entity-wallet-onboarding-profile-v1"
VERSION = "1.0.0"
LOGIN_SCHEMA = "entity-wallet-device-login-v1"

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


IDENTITY = _load("wallet_onboarding_identity", "src/01_Core_Runtime/identity/canonical_identity.py")
DOMAIN = _load("wallet_onboarding_domain", "src/22_Sovereign_Domain/core/canonical_domain.py")
AUTHORITY = _load(
    "wallet_onboarding_authority",
    "genesis_master/04_Entity_Registry/relationships/canonical_sovereign_authority.py",
)


def _now() -> int:
    return int(time.time() * 1000)


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(value if isinstance(value, (bytes, bytearray)) else _canon(value)).hexdigest()


def normalize_public_name(value: str) -> str:
    raw = str(value or "").strip().lower()
    if raw.endswith(".entity"):
        raw = raw[:-7]
    return DOMAIN.EntityDomainAuthority.normalize_name(raw)


def public_address(value: str) -> str:
    return normalize_public_name(value) + ".entity"


class EntityWalletOnboarding:
    """First-run sovereign identity, public-name, lineage and device-binding layer.

    Device metadata may bootstrap a DEVICE identity, but never a human or organization.
    A public .entity name is a signed display/name claim; canonical authority remains the Entity ID.
    """

    def __init__(self, state_dir: str | Path):
        self.state = Path(state_dir)
        self.identity = IDENTITY.EntityIdentityVault(self.state)
        self.domains = DOMAIN.EntityDomainAuthority(self.state, self.identity)
        self.authority = AUTHORITY.SovereignAuthorityRegistry(self.state, self.identity)
        self.root = self.state / "wallet" / "onboarding"
        self.profiles = self.root / "profiles"
        self.root.mkdir(parents=True, exist_ok=True)
        self.profiles.mkdir(parents=True, exist_ok=True)
        self.active_path = self.root / "active_profile.json"
        self.device_path = self.root / "device.json"

    @staticmethod
    def _alias_from_manifest(manifest: dict) -> str:
        aliases = [str(x).strip().lower() for x in manifest.get("aliases") or [] if str(x).strip()]
        entity_aliases = [x for x in aliases if x.endswith(".entity")]
        if entity_aliases:
            return entity_aliases[0]
        if aliases:
            return public_address(aliases[0])
        fallback = ".".join(
            p.lower() for p in "".join(
                c if c.isalnum() else " " for c in str(manifest.get("display_name") or "entity")
            ).split()
        )
        return public_address(fallback or ("entity-" + manifest["entity_id"][-8:]))

    def _existing_domain(self, entity_id: str) -> dict | None:
        if not self.domains.path.exists():
            return None
        db = sqlite3.connect(self.domains.path)
        db.row_factory = sqlite3.Row
        try:
            row = db.execute(
                """SELECT domain_id FROM domains
                   WHERE entity_id=? AND status='ACTIVE'
                   ORDER BY updated_at_ms DESC,created_at_ms DESC LIMIT 1""",
                (str(entity_id),),
            ).fetchone()
        finally:
            db.close()
        return self.domains.get_domain(row["domain_id"]) if row else None

    def ensure_public_name(self, entity_id: str, requested_name: str) -> dict:
        manifest = self.identity.load_manifest(str(entity_id))
        normalized = normalize_public_name(requested_name)
        domain = self._existing_domain(entity_id)
        if domain is None:
            domain = self.domains.create_domain(entity_id, namespace="entity", requested_name=normalized)
            claim = domain.get("name_claim")
            domain = self.domains.get_domain(domain["domain_id"])
        elif domain.get("current_name") == normalized:
            claim = {
                "normalized_name": normalized,
                "namespace": "entity",
                "conflict_state": "CLEAR",
                "existing": True,
            }
        else:
            claim = self.domains.claim_name(entity_id, domain["domain_id"], normalized)
            domain = self.domains.get_domain(domain["domain_id"])
        return {
            "entity_id": entity_id,
            "display_name": manifest["display_name"],
            "public_name": normalized + ".entity",
            "domain_id": domain["domain_id"],
            "name_claim": claim,
            "alias_is_authority": False,
            "entity_id_is_authority": True,
        }

    def _discover_device_identity(self) -> str | None:
        if self.device_path.is_file():
            try:
                d = json.loads(self.device_path.read_text(encoding="utf-8"))
                entity_id = str(d.get("device_entity_id") or "")
                manifest = self.identity.load_manifest(entity_id)
                if (
                    d.get("schema") == "entity-wallet-device-record-v1"
                    and d.get("device_information_is_not_user_identity") is True
                    and manifest.get("entity_type") == "system"
                ):
                    return entity_id
            except Exception:
                pass
        for manifest in self.identity.list_local():
            meta = dict(manifest.get("metadata") or {})
            if meta.get("wallet_device_identity") is True:
                return manifest["entity_id"]
        return None

    def ensure_device_identity(self, preferred_existing_entity_id: str | None = None) -> dict:
        if preferred_existing_entity_id:
            manifest = self.identity.load_manifest(str(preferred_existing_entity_id))
            if manifest.get("entity_type") != "system":
                raise ValueError("device identity must be a system Entity")
            device_id = manifest["entity_id"]
            created = False
        else:
            found = self._discover_device_identity()
            if found:
                manifest = self.identity.load_manifest(found)
                device_id = found
                created = False
            else:
                host = (socket.gethostname() or platform.node() or "ENTITY Device").strip()
                install_id = str(uuid.uuid4())
                alias_seed = "device-" + install_id.split("-")[0]
                manifest = self.identity.create(
                    f"{host} ENTITY Device",
                    "system",
                    aliases=[public_address(alias_seed)],
                    metadata={
                        "entity_subtype": "wallet_device",
                        "wallet_device_identity": True,
                        "software_device_identity": True,
                        "hardware_attested": False,
                        "installation_id": install_id,
                        "platform_system": platform.system(),
                        "platform_release": platform.release(),
                        "machine": platform.machine(),
                        "device_information_is_not_user_identity": True,
                        "device_identity_does_not_establish_person_or_organization": True,
                    },
                )
                device_id = manifest["entity_id"]
                created = True
        record = {
            "schema": "entity-wallet-device-record-v1",
            "device_entity_id": device_id,
            "display_name": manifest["display_name"],
            "created_by_onboarding": created,
            "device_information_is_not_user_identity": True,
            "updated_at_ms": _now(),
        }
        self.device_path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        return record

    def _ensure_relationship(
        self,
        entity_id: str,
        party_ref: str,
        relationship_type: str,
        *,
        scope: dict,
        evidence: dict,
    ) -> dict:
        for rel in self.authority.active_relationships(str(entity_id), str(party_ref)):
            if rel["relationship_type"] == str(relationship_type).upper():
                existing_scope = dict(rel.get("scope") or {})
                if all(existing_scope.get(k) == v for k, v in scope.items()):
                    return rel
        return self.authority.grant_relationship(
            str(entity_id),
            str(party_ref),
            str(relationship_type),
            scope=scope,
            evidence_origin="ENTITY_ASSERTION",
            evidence=evidence,
        )

    def _write_profile(self, body: dict) -> dict:
        principal = str(body["principal_entity_id"])
        active = str(body["active_entity_id"])
        signatures = {"principal": self.identity.sign(principal, body)}
        if active != principal:
            signatures["active_entity"] = self.identity.sign(active, body)
        profile = dict(body, signatures=signatures, profile_sha256=_sha(body))
        path = self.profiles / f"{body['profile_id']}.json"
        path.write_text(json.dumps(profile, indent=2, sort_keys=True), encoding="utf-8")
        self.active_path.write_text(
            json.dumps(
                {"schema": "entity-wallet-active-profile-v1", "profile_id": body["profile_id"], "updated_at_ms": _now()},
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return profile

    def _build_profile(
        self,
        *,
        principal_entity_id: str,
        active_entity_id: str,
        lineage_nodes: list[dict],
        device_entity_id: str,
        migrated_existing: bool,
    ) -> dict:
        body = {
            "schema": SCHEMA,
            "version": VERSION,
            "profile_id": "wallet-profile-" + secrets.token_hex(12),
            "principal_entity_id": str(principal_entity_id),
            "active_entity_id": str(active_entity_id),
            "device_entity_id": str(device_entity_id),
            "lineage": lineage_nodes,
            "display_path": " → ".join(node["public_name"] for node in lineage_nodes),
            "login_policy": {
                "mode": "DEVICE_BOUND_SIGNING_KEY",
                "password_required": False,
                "private_key_possession_required": True,
                "device_binding_required": True,
                "recovery_required_on_new_device": True,
            },
            "canonical_authority_is_entity_id": True,
            "public_name_is_alias_not_authority": True,
            "device_identity_is_not_user_identity": True,
            "protocol_origin_is_separate_from_user_lineage": True,
            "migrated_existing": bool(migrated_existing),
            "created_at_ms": _now(),
        }
        return self._write_profile(body)

    def create_profile(
        self,
        *,
        principal_display_name: str,
        principal_public_name: str,
        principal_entity_type: str = "person",
        organization_display_name: str | None = None,
        organization_public_name: str | None = None,
        organization_entity_type: str = "business",
        operate_as_organization: bool = True,
    ) -> dict:
        paddr = public_address(principal_public_name)
        principal = self.identity.create(
            principal_display_name,
            principal_entity_type,
            aliases=[paddr],
            metadata={
                "wallet_onboarding_created": True,
                "public_entity_name": paddr,
                "public_name_is_alias_not_authority": True,
            },
        )
        pclaim = self.ensure_public_name(principal["entity_id"], principal_public_name)
        lineage = [{
            "entity_id": principal["entity_id"],
            "display_name": principal["display_name"],
            "entity_type": principal["entity_type"],
            "public_name": pclaim["public_name"],
            "domain_id": pclaim["domain_id"],
            "role": "ROOT_PRINCIPAL",
        }]
        active = principal["entity_id"]

        if organization_display_name and organization_public_name:
            oaddr = public_address(organization_public_name)
            org = self.identity.create(
                organization_display_name,
                organization_entity_type,
                aliases=[oaddr],
                metadata={
                    "wallet_onboarding_created": True,
                    "public_entity_name": oaddr,
                    "public_name_is_alias_not_authority": True,
                    "lineage_parent_entity_id": principal["entity_id"],
                },
            )
            oclaim = self.ensure_public_name(org["entity_id"], organization_public_name)
            self._ensure_relationship(
                org["entity_id"],
                principal["entity_id"],
                "SOVEREIGN_AUTHORITY",
                scope={
                    "wallet_lineage_parent": True,
                    "organization_control": True,
                    "asset_ownership_not_implied": True,
                },
                evidence={"profile": SCHEMA},
            )
            lineage.append({
                "entity_id": org["entity_id"],
                "display_name": org["display_name"],
                "entity_type": org["entity_type"],
                "public_name": oclaim["public_name"],
                "domain_id": oclaim["domain_id"],
                "role": "OPERATING_ENTITY",
            })
            if operate_as_organization:
                active = org["entity_id"]

        device = self.ensure_device_identity()
        self._ensure_relationship(
            principal["entity_id"],
            device["device_entity_id"],
            "POSSESSION",
            scope={
                "wallet_device_bound": True,
                "device_possession_not_identity": True,
                "device_possession_not_ownership": True,
            },
            evidence={"profile": SCHEMA},
        )
        return self._build_profile(
            principal_entity_id=principal["entity_id"],
            active_entity_id=active,
            lineage_nodes=lineage,
            device_entity_id=device["device_entity_id"],
            migrated_existing=False,
        )

    def adopt_existing(
        self,
        *,
        principal_entity_id: str,
        active_entity_id: str | None = None,
        device_entity_id: str | None = None,
    ) -> dict:
        principal = self.identity.load_manifest(str(principal_entity_id))
        active_id = str(active_entity_id or principal_entity_id)
        active = self.identity.load_manifest(active_id)
        paddr = self._alias_from_manifest(principal)
        pclaim = self.ensure_public_name(principal["entity_id"], paddr)
        lineage = [{
            "entity_id": principal["entity_id"],
            "display_name": principal["display_name"],
            "entity_type": principal["entity_type"],
            "public_name": pclaim["public_name"],
            "domain_id": pclaim["domain_id"],
            "role": "ROOT_PRINCIPAL",
        }]
        if active_id != principal["entity_id"]:
            aaddr = self._alias_from_manifest(active)
            aclaim = self.ensure_public_name(active_id, aaddr)
            self._ensure_relationship(
                active_id,
                principal["entity_id"],
                "SOVEREIGN_AUTHORITY",
                scope={
                    "wallet_lineage_parent": True,
                    "organization_control": True,
                    "asset_ownership_not_implied": True,
                },
                evidence={"profile": SCHEMA, "migration": True},
            )
            lineage.append({
                "entity_id": active_id,
                "display_name": active["display_name"],
                "entity_type": active["entity_type"],
                "public_name": aclaim["public_name"],
                "domain_id": aclaim["domain_id"],
                "role": "OPERATING_ENTITY",
            })
        device = self.ensure_device_identity(device_entity_id)
        self._ensure_relationship(
            principal["entity_id"],
            device["device_entity_id"],
            "POSSESSION",
            scope={
                "wallet_device_bound": True,
                "device_possession_not_identity": True,
                "device_possession_not_ownership": True,
            },
            evidence={"profile": SCHEMA, "migration": True},
        )
        return self._build_profile(
            principal_entity_id=principal["entity_id"],
            active_entity_id=active_id,
            lineage_nodes=lineage,
            device_entity_id=device["device_entity_id"],
            migrated_existing=True,
        )

    def _verify_profile(self, profile: dict) -> bool:
        try:
            if profile.get("schema") != SCHEMA:
                return False
            body = {k: v for k, v in profile.items() if k not in {"signatures", "profile_sha256"}}
            if profile.get("profile_sha256") != _sha(body):
                return False
            signatures = dict(profile.get("signatures") or {})
            principal = self.identity.load_manifest(str(body["principal_entity_id"]))
            if not self.identity.verify_signature(principal, body, dict(signatures.get("principal") or {})):
                return False
            if body["active_entity_id"] != body["principal_entity_id"]:
                active = self.identity.load_manifest(str(body["active_entity_id"]))
                if not self.identity.verify_signature(active, body, dict(signatures.get("active_entity") or {})):
                    return False
            self.identity.load_manifest(str(body["device_entity_id"]))
            return True
        except Exception:
            return False

    def profile(self, profile_id: str) -> dict:
        path = self.profiles / f"{profile_id}.json"
        if not path.is_file():
            raise KeyError("wallet onboarding profile not found")
        profile = json.loads(path.read_text(encoding="utf-8"))
        if not self._verify_profile(profile):
            raise RuntimeError("wallet onboarding profile verification failed")
        return profile

    def list_profiles(self) -> list[dict]:
        out = []
        for path in sorted(self.profiles.glob("wallet-profile-*.json")):
            try:
                out.append(self.profile(path.stem))
            except Exception:
                continue
        return out

    def active_profile(self) -> dict | None:
        if not self.active_path.is_file():
            return None
        try:
            active = json.loads(self.active_path.read_text(encoding="utf-8"))
            return self.profile(str(active["profile_id"]))
        except Exception:
            return None

    def profile_for_entity(self, entity_id: str) -> dict | None:
        target = str(entity_id)
        active = self.active_profile()
        if active and active.get("active_entity_id") == target:
            return active
        for profile in self.list_profiles():
            if profile.get("active_entity_id") == target:
                return profile
        return None

    def set_active(self, profile_id: str) -> dict:
        profile = self.profile(profile_id)
        self.active_path.write_text(
            json.dumps(
                {"schema": "entity-wallet-active-profile-v1", "profile_id": profile_id, "updated_at_ms": _now()},
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return profile

    def authenticate(self, profile: dict | None = None) -> dict:
        profile = profile or self.active_profile()
        if not profile or not self._verify_profile(profile):
            return {"authenticated": False, "reason": "profile_missing_or_invalid"}
        current_device = self._discover_device_identity()
        if not current_device or current_device != profile["device_entity_id"]:
            return {
                "authenticated": False,
                "reason": "device_binding_mismatch",
                "recovery_or_rebind_required": True,
            }
        challenge = {
            "schema": LOGIN_SCHEMA,
            "profile_id": profile["profile_id"],
            "active_entity_id": profile["active_entity_id"],
            "device_entity_id": profile["device_entity_id"],
            "nonce": secrets.token_hex(32),
            "created_at_ms": _now(),
        }
        active_manifest = self.identity.load_manifest(profile["active_entity_id"])
        active_sig = self.identity.sign(profile["active_entity_id"], challenge)
        if not self.identity.verify_signature(active_manifest, challenge, active_sig):
            return {"authenticated": False, "reason": "active_identity_signature_failed"}
        device_manifest = self.identity.load_manifest(profile["device_entity_id"])
        device_sig = self.identity.sign(profile["device_entity_id"], challenge)
        if not self.identity.verify_signature(device_manifest, challenge, device_sig):
            return {"authenticated": False, "reason": "device_signature_failed"}
        return {
            "authenticated": True,
            "profile_id": profile["profile_id"],
            "principal_entity_id": profile["principal_entity_id"],
            "active_entity_id": profile["active_entity_id"],
            "device_entity_id": profile["device_entity_id"],
            "display_path": profile["display_path"],
            "mode": "DEVICE_BOUND_SIGNING_KEY",
            "password_used": False,
            "entity_id_is_authority": True,
        }

    def status(self) -> dict:
        active = self.active_profile()
        return {
            "ready": True,
            "schema": SCHEMA,
            "version": VERSION,
            "profile_count": len(self.list_profiles()),
            "active_profile_id": active.get("profile_id") if active else None,
            "first_run_required": active is None,
            "device_identity_auto_bootstrap": True,
            "device_information_creates_user_identity": False,
            "public_name_is_alias_not_authority": True,
            "login_mode": "DEVICE_BOUND_SIGNING_KEY",
        }
