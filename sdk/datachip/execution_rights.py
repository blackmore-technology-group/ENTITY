"""Experimental, issuer-side EXECUTE rights for ENTITY DataChips.

New, distinct protocol. The stable ENTITY EDCF v0.2 export grant does NOT confer
execution. This module NEVER creates keys, deploys an application, or considers
an asset wallet entry proof of entitlement. Production KMS, revocation-state,
licensing, host identity, and hardware-backed clocks are external fail-closed gates.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
import json
import re
from typing import Any

from .authority_bridge import _live_passport_record

GRANT_SCHEMA = "entity-edc-execute-grant-v0.1"
REVOCATION_SCHEMA = "entity-edc-execute-revocations-v0.1"
GRANT_DOMAIN = b"ENTITY:EDC:EXECUTE-GRANT:v0.1\x00"
REVOCATION_DOMAIN = b"ENTITY:EDC:EXECUTE-REVOKE:v0.1\x00"
GRANT_LIFETIME_LIMIT = 900
REVOCATION_LIFETIME_LIMIT = 900
ID_RE = re.compile(r"^[A-Za-z0-9:_./@-]{1,200}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
EXECUTE_ACTIONS = frozenset(("EXECUTE", "DATAPLANE:EXECUTE"))

class ExecutionDenied(PermissionError):
    """Default-deny execution rights or invalid signed state."""

def _require(cond: bool, why: str):
    if not cond:
        raise ExecutionDenied(why)

def _id(value: Any) -> str:
    _require(type(value) is str and ID_RE.fullmatch(value) is not None,
             "invalid ENTITY identity")
    return value

def _sha(value: Any) -> str:
    _require(type(value) is str and SHA_RE.fullmatch(value) is not None,
             "invalid SHA-256 identity")
    return value

def _time(value: Any) -> int:
    _require(type(value) is int and 0 <= value <= 4102444800,
             "invalid authority timestamp")
    return value

def _canonical(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf8")

_GRANT_FIELDS = frozenset(("schema", "authority_key_id", "grant_id", "passport_id",
    "passport_sha256", "object_id", "controller_entity_id", "chip_id",
    "content_sha256", "assembly_sha256", "subject", "audience",
    "device_id", "action", "not_before", "expires_at"))
_REVOKE_FIELDS = frozenset(("schema", "authority_key_id", "sequence",
    "issued_at", "valid_until", "covered_rights_keys", "revoked_rights_keys",
    "revoked_passport_ids", "revoked_grant_ids"))

def _verify(envelope: Any, schema: str, domain: bytes,
            keys: Mapping[str, bytes], required: frozenset[str]) -> dict:
    _require(type(envelope) is dict and set(envelope) == {"body", "signature"},
             "signed authority envelope missing")
    body = envelope["body"]
    signature = envelope["signature"]
    _require(type(body) is dict and body.get("schema") == schema
             and set(body) == required, "unsupported signed authority version")
    _require(type(signature) is str and len(signature) == 128,
             "signature malformed")
    kid = _id(body["authority_key_id"])
    _require(isinstance(keys, Mapping) and kid in keys,
             "authority key not independently trusted")
    raw = keys[kid]
    _require(type(raw) is bytes and len(raw) == 32,
             "invalid pinned issuer key")
    try:
        Ed25519PublicKey.from_public_bytes(raw).verify(
            bytes.fromhex(signature), domain + _canonical(body))
    except (ValueError, TypeError, InvalidSignature) as exc:
        raise ExecutionDenied("issuer signature invalid") from exc
    return body

def active_execute_passport(registry: Any, passport_id: str, *,
                            object_id: str, controller_id: str) -> dict:
    """Use real ENTITY RightsPassportRegistry signed body AND live SQLite status."""
    for value in (passport_id, object_id, controller_id):
        _id(value)
    try:
        row = _live_passport_record(registry, passport_id)
        passport = registry.get(passport_id)
        proof = registry.verify(passport)
    except Exception as exc:
        raise ExecutionDenied("authoritative Rights Passport unavailable") from exc
    _require(proof.get("valid") is True, "passport controller signature invalid")
    _require(passport.get("schema") == "entity-v3-rights-passport-v1",
             "unknown Rights Passport schema")
    for field, expected in (("passport_id", passport_id), ("object_id", object_id),
                            ("controller_entity_id", controller_id),
                            ("version", row["version"]),
                            ("passport_sha256", row["passport_sha256"])):
        _require(passport.get(field) == expected and row.get(field) == expected,
                 "signed passport versus live status mismatch")
    _require(passport.get("status") == "ACTIVE", "signed passport not active")
    rules = passport.get("rights")
    _require(type(rules) is list and bool(rules), "no execution policy")
    allow = False
    for rule in rules:
        _require(type(rule) is dict and type(rule.get("actions")) is list,
                 "invalid Rights Passport rule")
        actions = {v.upper() for v in rule["actions"] if type(v) is str}
        if not actions.intersection(EXECUTE_ACTIONS):
            continue
        _require(not rule.get("conditions") and not rule.get("obligations"),
                 "conditional execution requires independent policy interpreter")
        if rule.get("effect") == "PROHIBIT":
            raise ExecutionDenied("execution explicitly prohibited")
        _require(rule.get("effect") == "ALLOW", "unknown execution rule effect")
        allow = True
    _require(allow, "export or wallet access is NOT execute authority")
    return {"passport_id": passport_id, "passport_sha256": _sha(row["passport_sha256"]),
            "controller_entity_id": controller_id, "object_id": object_id,
            "signed_passport_verified": True, "live_passport_checked": True,
            "explicit_execute": True, "export_granted": False}

def issue_execution_grant(registry: Any, *, passport_id: str, object_id: str,
                          controller_id: str, chip_id: str, content_sha256: str,
                          assembly_sha256: str, subject: str, audience: str,
                          device_id: str, authority_key_id: str, grant_id: str,
                          now: int, valid_seconds: int,
                          controller_authorization: Callable[..., bool],
                          authorized_signer: Callable[[bytes], bytes],
                          pinned_issuer_keys: Mapping[str, bytes]) -> dict:
    """Issuer-side only: authenticated controller + live registry + external signer."""
    for v in (passport_id, object_id, controller_id, chip_id, subject, audience,
              device_id, authority_key_id, grant_id):
        _id(v)
    _sha(content_sha256)
    _sha(assembly_sha256)
    _time(now)
    _require(type(valid_seconds) is int and 1 <= valid_seconds <= GRANT_LIFETIME_LIMIT,
             "grant period outside bounds")
    _require(callable(controller_authorization) and callable(authorized_signer),
             "authenticated controller and KMS/HSM signer required")
    first = active_execute_passport(registry, passport_id, object_id=object_id,
                                    controller_id=controller_id)
    decision = controller_authorization(
        controller_entity_id=controller_id, subject=subject, app_id=audience,
        passport_id=passport_id, object_id=object_id, chip_id=chip_id,
        device_id=device_id, action="dataplane:execute")
    _require(decision is True, "controller did not authorize execute")
    second = active_execute_passport(registry, passport_id, object_id=object_id,
                                     controller_id=controller_id)
    _require(second["passport_sha256"] == first["passport_sha256"],
             "passport changed during authorization")
    body = {"schema": GRANT_SCHEMA, "authority_key_id": authority_key_id,
            "grant_id": grant_id, "passport_id": passport_id,
            "passport_sha256": first["passport_sha256"],
            "object_id": object_id, "controller_entity_id": controller_id,
            "chip_id": chip_id, "content_sha256": content_sha256,
            "assembly_sha256": assembly_sha256, "subject": subject,
            "audience": audience, "device_id": device_id,
            "action": "dataplane:execute",
            "not_before": now, "expires_at": now + valid_seconds}
    signature = authorized_signer(GRANT_DOMAIN + _canonical(body))
    _require(type(signature) is bytes and len(signature) == 64,
             "external signing service denied issuance")
    grant = {"body": body, "signature": signature.hex()}
    _verify(grant, GRANT_SCHEMA, GRANT_DOMAIN, pinned_issuer_keys, _GRANT_FIELDS)
    return grant

def verify_execution_right(grant: dict, snapshot: dict, *,
                           pinned_issuer_keys: Mapping[str, bytes],
                           pinned_revocation_keys: Mapping[str, bytes],
                           subject: str, audience: str, device_id: str,
                           chip_id: str, content_sha256: str, assembly_sha256: str,
                           license_entitlement: Callable[..., bool],
                           device_identity: Callable[..., bool],
                           protected_min_sequence: int, now: int,
                           expected_passport_sha256: str | None = None) -> dict:
    """Consumer: separately verify signed grant, revocation, license and identity."""
    _time(now)
    for value in (subject, audience, device_id, chip_id): _id(value)
    for value in (content_sha256, assembly_sha256): _sha(value)
    _require(type(protected_min_sequence) is int and protected_min_sequence >= 0,
             "protected revocation checkpoint missing")
    body = _verify(grant, GRANT_SCHEMA, GRANT_DOMAIN, pinned_issuer_keys, _GRANT_FIELDS)
    rev = _verify(snapshot, REVOCATION_SCHEMA, REVOCATION_DOMAIN,
                  pinned_revocation_keys, _REVOKE_FIELDS)
    for field in ("grant_id", "passport_id", "object_id", "controller_entity_id"):
        _id(body[field])
    for field in ("passport_sha256", "content_sha256", "assembly_sha256"):
        _sha(body[field])
    _require(body["action"] == "dataplane:execute",
             "export grant cannot authorize execution")
    _require((body["subject"], body["audience"], body["device_id"])
             == (subject, audience, device_id), "subject/app/device mismatch")
    _require((body["chip_id"], body["content_sha256"], body["assembly_sha256"])
             == (chip_id, content_sha256, assembly_sha256), "assembly/content mismatch")
    if expected_passport_sha256 is not None:
        _require(body["passport_sha256"] == _sha(expected_passport_sha256),
                 "Rights Passport version differs")
    start = _time(body["not_before"])
    end = _time(body["expires_at"])
    _require(start < end and end - start <= GRANT_LIFETIME_LIMIT
             and start <= now < end, "execution grant not current")
    first = _time(rev["issued_at"])
    last = _time(rev["valid_until"])
    _require(first <= now < last and last - first <= REVOCATION_LIFETIME_LIMIT,
             "revocation snapshot stale/future")
    sequence = rev["sequence"]
    _require(type(sequence) is int and sequence >= protected_min_sequence,
             "revocation rollback")
    for field in ("covered_rights_keys", "revoked_rights_keys",
                  "revoked_passport_ids", "revoked_grant_ids"):
        values = rev[field]
        _require(type(values) is list and len(values) <= 4096
                 and all(type(v) is str and ID_RE.fullmatch(v) for v in values)
                 and values == sorted(set(values)), "invalid revocation list")
    _require(body["authority_key_id"] in rev["covered_rights_keys"],
             "revocation status does not cover issuer")
    _require(body["authority_key_id"] not in rev["revoked_rights_keys"]
             and body["grant_id"] not in rev["revoked_grant_ids"]
             and body["passport_id"] not in rev["revoked_passport_ids"],
             "execution grant revoked")
    _require(callable(license_entitlement) and callable(device_identity),
             "licensed rights or device verification unavailable")
    _require(license_entitlement(action="dataplane:execute",
        passport_id=body["passport_id"], subject=subject, app_id=audience,
        chip_id=chip_id, grant_id=body["grant_id"]) is True,
        "license entitlement not active")
    _require(device_identity(device_id=device_id, subject=subject,
        audience=audience, action="dataplane:execute") is True,
        "device identity not authenticated")
    return {"schema": "entity-edc-verified-execution-v0.1",
            "chip_id": chip_id, "content_sha256": content_sha256,
            "assembly_sha256": assembly_sha256, "grant_id": body["grant_id"],
            "passport_id": body["passport_id"], "subject": subject,
            "audience": audience, "device_id": device_id,
            "issuer_signature_verified": True, "revocation_signature_verified": True,
            "license_verified": True, "device_identity_adapter_verified": True,
            "execution_right_verified": True, "export_right_verified": False,
            "revocation_sequence": sequence,
            "expires_at": min(end, last),
            "production_issuer_connected": False,
            "hardware_identity_attested": False,
            "production_ready": False}

def sign_revocation_from_authority(*, key_id: str, sequence: int, now: int,
    valid_seconds: int, authoritative_status: Callable[..., dict],
    authorized_signer: Callable[[bytes], bytes],
    pinned_revocation_keys: Mapping[str, bytes]) -> dict:
    """Issuer-side: authenticated complete current ledger and external KMS signer."""
    _id(key_id)
    _time(now)
    _require(type(sequence) is int and sequence > 0, "bad sequence")
    _require(type(valid_seconds) is int and 1 <= valid_seconds <= REVOCATION_LIFETIME_LIMIT,
             "revocation lifetime too long")
    _require(callable(authoritative_status) and callable(authorized_signer),
             "authoritative revocation ledger and signer unavailable")
    current = authoritative_status(key_id=key_id, sequence=sequence)
    _require(type(current) is dict and current.get("complete") is True
             and type(current.get("sequence")) is int
             and current["sequence"] == sequence, "incomplete ledger state")
    values = {}
    for field in ("covered_rights_keys", "revoked_rights_keys",
                  "revoked_passport_ids", "revoked_grant_ids"):
        entries = current.get(field)
        _require(type(entries) in (list, tuple) and len(entries) <= 4096,
                 "incomplete revocation scope")
        values[field] = sorted(set(_id(x) for x in entries))
    _require(bool(values["covered_rights_keys"]), "issuer coverage absent")
    body = {"schema": REVOCATION_SCHEMA, "authority_key_id": key_id,
            "sequence": sequence, "issued_at": now,
            "valid_until": now + valid_seconds, **values}
    sig = authorized_signer(REVOCATION_DOMAIN + _canonical(body))
    _require(type(sig) is bytes and len(sig) == 64,
             "revocation signer not available")
    result = {"body": body, "signature": sig.hex()}
    _verify(result, REVOCATION_SCHEMA, REVOCATION_DOMAIN,
            pinned_revocation_keys, _REVOKE_FIELDS)
    return result
