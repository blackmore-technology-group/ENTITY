"""Fail-closed read-only bridge to ENTITY's authoritative RightsPassportRegistry.

This module is an *issuer-side* adapter: no key material or SQLite read permission
is exposed to EDC consumers. Grant issuance requires a trusted authenticated
controller/subject authorization callback AND externally provisioned signing key.
There is no self-service key minting or inference of legal title from bytes.
"""
from __future__ import annotations

from pathlib import Path
from contextlib import closing
import sqlite3
from typing import Any, Callable

from .rights import issue_grant
from .processor import DataChipError

_EXPORT_ACTIONS = {"EXPORT", "DATA_EXPORT"}


def _live_passport_record(registry: Any, passport_id: str) -> dict[str, Any]:
    """Check authoritative DB status separately from the signed passport body."""
    if not isinstance(passport_id, str) or not passport_id or len(passport_id) > 200:
        raise PermissionError("invalid passport identity")
    path = Path(registry.path).resolve(strict=True)
    if not path.is_file():
        raise PermissionError("Rights Passport registry is unavailable")
    # SQLite read-only ensures the bridge cannot migrate/change production records.
    # Do not use immutable=1: the live registry may have committed WAL updates.
    uri = path.as_uri() + "?mode=ro"
    try:
        with closing(sqlite3.connect(uri, uri=True, timeout=3.0)) as db:
            db.row_factory = sqlite3.Row
            row = db.execute(
                "SELECT passport_id,object_id,controller_entity_id,version,"
                "passport_sha256,status FROM passports WHERE passport_id=?",
                (passport_id,),
            ).fetchone()
            if row is None:
                raise PermissionError("Rights Passport not found")
            if row["status"] != "ACTIVE":
                raise PermissionError("Rights Passport is not active")
            collision = db.execute(
                "SELECT COUNT(*) FROM passports WHERE object_id=? "
                "AND controller_entity_id=? AND status='ACTIVE'",
                (row["object_id"], row["controller_entity_id"]),
            ).fetchone()[0]
            if collision != 1:
                raise PermissionError("ambiguous active Rights Passport versions")
            newer = db.execute(
                "SELECT COUNT(*) FROM supersessions WHERE old_passport_id=?",
                (passport_id,),
            ).fetchone()[0]
            if newer:
                raise PermissionError("Rights Passport has been superseded")
            return dict(row)
    except sqlite3.Error as exc:
        raise PermissionError("authoritative registry unavailable/invalid") from exc


def inspect_active_passport(registry: Any, passport_id: str, *,
                            expected_object_id: str,
                            expected_controller: str) -> dict[str, Any]:
    """Use Registry.get/verify for cryptographic authenticity and DB for liveness.

    This *does not* translate a passport's generic signature into permission.
    The rules must explicitly permit export and contain no conditional logic
    that this adapter lacks the information to evaluate.
    """
    row = _live_passport_record(registry, passport_id)
    try:
        passport = registry.get(passport_id)
        proof = registry.verify(passport)
    except Exception as exc:
        raise PermissionError("passport signature verification unavailable") from exc
    if proof.get("valid") is not True:
        raise PermissionError("Rights Passport signature/hash invalid")
    if (passport.get("passport_id") != passport_id or
            passport.get("object_id") != expected_object_id or
            passport.get("controller_entity_id") != expected_controller or
            passport.get("passport_sha256") != row["passport_sha256"] or
            passport.get("version") != row["version"] or
            row["object_id"] != expected_object_id or
            row["controller_entity_id"] != expected_controller):
        raise PermissionError("Rights Passport identity/status mismatch")
    if passport.get("status") != "ACTIVE":
        raise PermissionError("passport body is not active")
    rule_allow = False
    rights = passport.get("rights")
    if type(rights) is not list or not rights:
        raise PermissionError("no explicit export right")
    for rule in rights:
        if type(rule) is not dict:
            raise PermissionError("invalid rights rule")
        actions = rule.get("actions")
        if type(actions) is not list:
            raise PermissionError("invalid actions")
        if not (_EXPORT_ACTIONS & {a.upper() for a in actions if type(a) is str}):
            continue
        effect = rule.get("effect")
        # Generic conditions, obligations and REQUIRE effects require a full
        # contextual policy engine. Never silently discard them.
        if rule.get("conditions") or rule.get("obligations"):
            raise PermissionError("conditional/obligated export needs policy interpreter")
        if effect == "PROHIBIT":
            raise PermissionError("export is prohibited")
        if effect != "ALLOW":
            raise PermissionError("export requires unsupported additional conditions")
        rule_allow = True
    if not rule_allow:
        raise PermissionError("no unconditional export ALLOW rule")
    return {
        "schema": "entity-edc-active-rights-inspection-v0.1",
        "passport_id": passport_id,
        "object_id": expected_object_id,
        "controller_entity_id": expected_controller,
        "passport_sha256": row["passport_sha256"],
        "active_verified": True,
        "unconditional_export_allow": True,
        "registry_path_is_private": True,
    }


def issue_authorized_datachip_grant(registry: Any, *, passport_id: str,
        object_id: str, controller_entity_id: str, chip_id: str,
        authenticated_subject: str, audience: str,
        authenticated_request_authorized: Callable[..., bool],
        issuer_private_key: Any, issuer_key_id: str,
        now: int, valid_seconds: int = 900) -> dict[str, Any]:
    """Issuer-side only. Caller MUST securely authenticate controller's grant.

    The signer is externally injected (production: HSM/KMS); this reference
    module never reads a signing key from disk or exposes signing via network.
    """
    if type(now) is not int or type(valid_seconds) is not int or not 1 <= valid_seconds <= 900:
        raise PermissionError("grant expiry window not permitted")
    if not callable(authenticated_request_authorized):
        raise PermissionError("external authenticated policy decision required")
    evidence = inspect_active_passport(registry, passport_id,
                expected_object_id=object_id,
                expected_controller=controller_entity_id)
    decision = authenticated_request_authorized(
        controller_entity_id=controller_entity_id,
        subject=authenticated_subject,
        app_id=audience,
        passport_id=passport_id,
        object_id=object_id,
        chip_id=chip_id,
        action="dataplane:export",
    )
    if decision is not True:
        raise PermissionError("authenticated controller did not authorize this principal")
    # Recheck liveness after the separately authenticated controller decision.
    # Cross-process supersession can still race with issuance; production
    # requires transactional authority attestations and revocation publication.
    again = inspect_active_passport(registry, passport_id,
                expected_object_id=object_id,
                expected_controller=controller_entity_id)
    if again["passport_sha256"] != evidence["passport_sha256"]:
        raise PermissionError("Rights Passport changed during authorization")
    return issue_grant(
        issuer_private_key,
        authority_key_id=issuer_key_id, chip_id=chip_id,
        subject=authenticated_subject, audience=audience,
        rights_passport_ref=evidence["passport_id"],
        not_before=now, expires_at=now + valid_seconds,
    )
