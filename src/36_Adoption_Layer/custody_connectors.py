from __future__ import annotations
from typing import Any
import hashlib, json, time

PROVIDERS = {
    "AWS_S3", "AZURE_BLOB", "GOOGLE_CLOUD_STORAGE", "SNOWFLAKE", "DATABRICKS",
    "POSTGRESQL", "SQL_SERVER", "LOCAL_FILESYSTEM", "HTTP_API",
}

def now_ms() -> int:
    return int(time.time() * 1000)

def canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()

def digest(value: Any) -> str:
    raw = value if isinstance(value, (bytes, bytearray)) else canon(value)
    return hashlib.sha256(raw).hexdigest()

def sha256_hex(value: str) -> str:
    value = str(value).lower()
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("content_sha256 must be lowercase SHA-256")
    return value

class CustodyConnectorRegistry:
    """Provider-neutral locators. Connectors identify custody; they never confer authority."""
    @staticmethod
    def locator(entity_object_id: str, provider: str, locator: str, content_sha256: str, *,
                account_scope_ref: str | None = None, region: str | None = None,
                version_ref: str | None = None, metadata: dict | None = None) -> dict:
        provider = str(provider).upper()
        if provider not in PROVIDERS:
            raise ValueError("unsupported custody provider")
        if not str(entity_object_id) or not str(locator):
            raise ValueError("entity object id and locator required")
        body = {
            "schema": "entity-v3-custody-locator-v1",
            "entity_object_id": str(entity_object_id),
            "provider": provider,
            "locator": str(locator),
            "content_sha256": sha256_hex(content_sha256),
            "account_scope_ref": account_scope_ref,
            "region": str(region).upper() if region else None,
            "version_ref": version_ref,
            "metadata": dict(metadata or {}),
            "provider_is_authority": False,
            "credentials_included": False,
            "entity_identity_changes_with_provider": False,
        }
        body["locator_sha256"] = digest(body)
        return body

    @staticmethod
    def migration(old_locator: dict, new_locator: dict, *, evidence_sha256: str,
                  actor_entity_id: str) -> dict:
        if old_locator.get("entity_object_id") != new_locator.get("entity_object_id"):
            raise ValueError("provider migration must preserve ENTITY object id")
        if old_locator.get("provider_is_authority") is not False or new_locator.get("provider_is_authority") is not False:
            raise ValueError("custody cannot become authority during migration")
        evidence_sha256 = sha256_hex(evidence_sha256)
        return {
            "schema": "entity-v3-custody-migration-v1",
            "entity_object_id": old_locator["entity_object_id"],
            "from_locator_sha256": old_locator.get("locator_sha256") or digest(old_locator),
            "to_locator_sha256": new_locator.get("locator_sha256") or digest(new_locator),
            "actor_entity_id": str(actor_entity_id),
            "evidence_sha256": evidence_sha256,
            "created_at_ms": now_ms(),
            "entity_identity_preserved": True,
            "authority_transfer_implied": False,
        }

    @staticmethod
    def supported() -> list[str]:
        return sorted(PROVIDERS)
