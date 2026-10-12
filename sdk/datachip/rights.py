"""Ed25519 signed offline DataChip grant + revocation receipt (experimental).

Verifies *delegated signed export claims* using trusted OUT-OF-BAND public
keys and a separately signed fresh revocation snapshot. This DOES NOT
establish legal ownership, authenticate the human device user, or verify
an ENTITY Rights Passport's authoritative state without a trusted bridge.
"""
from __future__ import annotations

from collections.abc import Mapping
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import os
import re
from typing import Any

from .processor import DataChipError, _canon
from .formula_chip import export_formula, inspect_formula

GRANT_SCHEMA="entity-edc-signed-rights-grant-v0.2"
REVOCATION_SCHEMA="entity-edc-signed-revocations-v0.2"
GRANT_PREFIX=b"ENTITY:EDC:GRANT:v0.2\0"
REVOCATION_PREFIX=b"ENTITY:EDC:REVOKE:v0.2\0"
MAX_SNAPSHOT_AGE=24*60*60
MAX_GRANT_LIFETIME=30*24*60*60
_ID=re.compile(r"^[A-Za-z0-9:_./@-]{1,200}$")
_HASH=re.compile(r"^[0-9a-f]{32}$")
_ALLOWED_ACTION="dataplane:export"


def _id(value: Any) -> str:
    if type(value) is not str or not _ID.fullmatch(value):
        raise DataChipError("invalid grant identity/reference")
    return value


def _timestamp(value: Any) -> int:
    if type(value) is not int or not 0 <= value <= 4102444800:
        raise DataChipError("invalid timestamp")
    return value


def _key(keys: Mapping[str,bytes],kid:str) -> Ed25519PublicKey:
    if not isinstance(keys,Mapping) or kid not in keys:
        raise PermissionError("untrusted authority key")
    key=keys[kid]
    if type(key) is not bytes or len(key)!=32:
        raise PermissionError("invalid pinned authority key")
    return Ed25519PublicKey.from_public_bytes(key)


def _validate_signed(signed:Any, body_keys:set[str],schema:str) -> dict[str,Any]:
    if type(signed) is not dict or set(signed)!={"body","signature"}:
        raise PermissionError("invalid signed envelope")
    body=signed["body"]
    if type(body) is not dict or set(body)!=body_keys or body.get("schema")!=schema:
        raise PermissionError("unsupported signed claim")
    signature=signed["signature"]
    if type(signature) is not str or len(signature)!=128:
        raise PermissionError("invalid signature")
    try:
        sig=bytes.fromhex(signature)
    except ValueError as e:
        raise PermissionError("invalid signature format") from e
    return body


def _verify(sig_hex:str, prefix:bytes, body:dict[str,Any],
            keys:Mapping[str,bytes], kid:str):
    try:
        _key(keys,kid).verify(bytes.fromhex(sig_hex), prefix + _canon(body))
    except (InvalidSignature,ValueError,TypeError) as e:
        raise PermissionError("invalid authorized signature") from e


def public_key_bytes(private:Ed25519PrivateKey) -> bytes:
    """Dev/issuer-side helper; consumer needs only the public key."""
    return private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


def issue_grant(private:Ed25519PrivateKey, *, authority_key_id:str,
                chip_id:str, subject:str, audience:str,
                rights_passport_ref:str, not_before:int, expires_at:int,
                grant_id:str|None=None) -> dict[str,Any]:
    """Issuer-side helper; deploy only inside an explicitly authorized signer."""
    for value in (authority_key_id,chip_id,subject,audience,rights_passport_ref):
        _id(value)
    first=_timestamp(not_before)
    last=_timestamp(expires_at)
    if last<=first or last-first>MAX_GRANT_LIFETIME:
        raise ValueError("invalid grant lifetime")
    nonce=_id(grant_id or "grant:"+os.urandom(16).hex())
    body={"schema":GRANT_SCHEMA,"authority_key_id":authority_key_id,
          "grant_id":nonce,"chip_id":chip_id,
          "subject":subject,"audience":audience,
          "action":_ALLOWED_ACTION,"rights_passport_ref":rights_passport_ref,
          "not_before":first,"expires_at":last}
    return {"body":body,"signature":private.sign(GRANT_PREFIX+_canon(body)).hex()}


def issue_revocation_snapshot(private:Ed25519PrivateKey, *,
                              authority_key_id:str,issued_at:int,
                              valid_until:int,revoked_grant_ids:tuple[str,...]=(),
                              revoked_rights_keys:tuple[str,...]=(),
                              covered_rights_keys:tuple[str,...]=()) -> dict[str,Any]:
    """Issuer-side helper: sign a bounded and complete revocation status list."""
    _id(authority_key_id)
    first=_timestamp(issued_at)
    last=_timestamp(valid_until)
    if last<=first or last-first>MAX_SNAPSHOT_AGE:
        raise ValueError("invalid revocation snapshot lifetime")
    grant_ids=sorted(set(_id(v) for v in revoked_grant_ids))
    key_ids=sorted(set(_id(v) for v in revoked_rights_keys))
    coverage=sorted(set(_id(v) for v in covered_rights_keys))
    if len(grant_ids)>4096 or len(key_ids)>1024 or len(coverage)>1024:
        raise ValueError("revocation list too large")
    body={"schema":REVOCATION_SCHEMA,"authority_key_id":authority_key_id,
          "issued_at":first,"valid_until":last,
          "revoked_grant_ids":grant_ids,"revoked_rights_keys":key_ids,
          "covered_rights_keys":coverage}
    return {"body":body,"signature":private.sign(REVOCATION_PREFIX+_canon(body)).hex()}


GRANT_KEYS={"schema","authority_key_id","grant_id","chip_id","subject",
            "audience","action","rights_passport_ref","not_before","expires_at"}
SNAPSHOT_KEYS={"schema","authority_key_id","issued_at","valid_until",
               "revoked_grant_ids","revoked_rights_keys","covered_rights_keys"}


def verify_grant(grant:Any, revocations:Any, *,
                 pinned_rights_keys:Mapping[str,bytes],
                 pinned_revocation_keys:Mapping[str,bytes],
                 trusted_subject:str, trusted_audience:str,
                 expected_chip_id:str, now:int) -> dict[str,Any]:
    """Independently verify signed delegated claims with pinned trust roots.

    trusted_subject and trusted_audience MUST come from a separately
    authenticated caller/session; a user-supplied name is not authentication.
    """
    clock=_timestamp(now)
    doc=_validate_signed(grant,GRANT_KEYS,GRANT_SCHEMA)
    rev=_validate_signed(revocations,SNAPSHOT_KEYS,REVOCATION_SCHEMA)
    for k in ("authority_key_id","grant_id","chip_id","subject","audience",
              "rights_passport_ref"):
        _id(doc[k])
    for k in ("authority_key_id",):
        _id(rev[k])
    if doc["action"]!=_ALLOWED_ACTION:
        raise PermissionError("requested action not authorized")
    _id(trusted_subject)
    _id(trusted_audience)
    _id(expected_chip_id)
    if (doc["chip_id"]!=expected_chip_id or doc["subject"]!=trusted_subject
            or doc["audience"]!=trusted_audience):
        raise PermissionError("grant is not scoped to this chip/principal/application")
    start=_timestamp(doc["not_before"])
    end=_timestamp(doc["expires_at"])
    if end<=start or end-start>MAX_GRANT_LIFETIME or not start<=clock<end:
        raise PermissionError("grant not currently valid")
    first=_timestamp(rev["issued_at"])
    last=_timestamp(rev["valid_until"])
    if last<=first or last-first>MAX_SNAPSHOT_AGE or not first<=clock<last:
        raise PermissionError("revocation proof expired or from future")
    if clock-first>MAX_SNAPSHOT_AGE:
        raise PermissionError("revocation check too old")
    for key,cap in (("revoked_grant_ids",4096),("revoked_rights_keys",1024),
                    ("covered_rights_keys",1024)):
        a=rev[key]
        if type(a) is not list or len(a)>cap:
            raise PermissionError("malformed revocation list")
        ids=[_id(v) for v in a]
        if ids != sorted(set(ids)):
            raise PermissionError("noncanonical revocation list")
    _verify(grant["signature"],GRANT_PREFIX,doc,
            pinned_rights_keys,doc["authority_key_id"])
    _verify(revocations["signature"],REVOCATION_PREFIX,rev,
            pinned_revocation_keys,rev["authority_key_id"])
    if doc["authority_key_id"] not in rev["covered_rights_keys"]:
        raise PermissionError("revocation proof does not cover this grant authority")
    if (doc["grant_id"] in rev["revoked_grant_ids"] or
            doc["authority_key_id"] in rev["revoked_rights_keys"]):
        raise PermissionError("grant or rights issuer revoked")
    return {"schema":"entity-edc-verified-delegated-right-v0.2",
            "issuer_signature_valid":True,
            "revocation_signature_valid":True,
            "grant_id":doc["grant_id"],
            "rights_passport_ref":doc["rights_passport_ref"],
            "chip_id":doc["chip_id"],"subject":doc["subject"],
            "audience":doc["audience"],"action":doc["action"],
            "valid_until":min(end,last),
            "bounds":"delegated-claim-only-not-legal-title-or-full-entity-policy"}


def authorized_formula_export(path:str, output:str, *,
                              grant:dict[str,Any], revocations:dict[str,Any],
                              pinned_rights_keys:Mapping[str,bytes],
                              pinned_revocation_keys:Mapping[str,bytes],
                              trusted_subject:str, trusted_audience:str,
                              now:int) -> dict[str,Any]:
    """Chip-bound verified delegation + explicit host identity, then safe export."""
    doc=inspect_formula(path)
    verified=verify_grant(grant,revocations,
                          pinned_rights_keys=pinned_rights_keys,
                          pinned_revocation_keys=pinned_revocation_keys,
                          trusted_subject=trusted_subject,
                          trusted_audience=trusted_audience,
                          expected_chip_id=doc["chip_id"],now=now)
    exported=export_formula(path,output,authorize=lambda action,manifest:
        action==verified["action"] and manifest["chip_id"]==verified["chip_id"])
    return {**exported,"grant_id":verified["grant_id"],
            "signed_delegation_verified":True}
