"""BTG Application DataChip bundle v0.1: signed, declarative app data lockfile.

A signed bundle does not execute code or grant OS access. It selects and verifies
local EDC artifacts under explicitly provided host storage locations.
"""
from __future__ import annotations

from collections.abc import Mapping
import hashlib
import re
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .processor import DataChipError, _canon, inspect_chip, verify_chip
from .formula_chip import inspect_formula, verify_formula

SCHEMA="btg-application-datachip-bundle-v0.1"
SIGN_DOMAIN=b"BTG:APPLICATION:DATABUNDLE:v0.1\x00"
KINDS={"geographic","spatial","wildlife","navigation","hud",
       "ai","safety","diagnostics","documents","policy","trip"}
PLATFORMS={"ios","android","windows","linux","macos"}
REF=re.compile(r"^[A-Za-z0-9][A-Za-z0-9:./@_-]{0,159}$")
SHA=re.compile(r"^[0-9a-f]{64}$")
MAX_MODULES=128


def _ref(x:Any) -> str:
    if type(x) is not str or not REF.fullmatch(x):
        raise DataChipError("invalid bundle identifier")
    return x


def _digest(x:Any) -> str:
    if type(x) is not str or not SHA.fullmatch(x):
        raise DataChipError("invalid bundle SHA-256")
    return x


def _check_modules(modules:Any) -> list[str]:
    if type(modules) is not list or not 1 <= len(modules) <= MAX_MODULES:
        raise DataChipError("invalid application module list")
    lookup={}
    for m in modules:
        if type(m) is not dict or set(m)!={"name","kind","chip_id","sha256","requires","data_right"}:
            raise DataChipError("malformed module definition")
        name=_ref(m["name"])
        if name in lookup:
            raise DataChipError("duplicate module name")
        if type(m["kind"]) is not str or m["kind"] not in KINDS:
            raise DataChipError("unsupported module kind")
        if type(m["chip_id"]) is not str or not (
            m["chip_id"].startswith("edc:formula:sha256:") or
            m["chip_id"].startswith("edc:sha256:")):
            raise DataChipError("unsupported chip id")
        suffix=m["chip_id"].split(":")[-1]
        _digest(suffix)
        _digest(m["sha256"])
        if type(m["data_right"]) is not str or m["data_right"] not in ("public","grant-required"):
            raise DataChipError("invalid data access class")
        deps=m["requires"]
        if type(deps) is not list or len(deps)>MAX_MODULES:
            raise DataChipError("invalid dependency list")
        for dep in deps:
            _ref(dep)
        if len(deps)!=len(set(deps)):
            raise DataChipError("duplicate dependency")
        lookup[name]=m
    visited=set()
    visiting=set()
    order=[]
    def visit(name:str):
        if name in visiting:
            raise DataChipError("cyclic module dependency")
        if name in visited:
            return
        if name not in lookup:
            raise DataChipError("unknown module dependency")
        visiting.add(name)
        for dep in lookup[name]["requires"]:
            visit(dep)
        visiting.remove(name)
        visited.add(name)
        order.append(name)
    for name in lookup:
        visit(name)
    return order


def _validated_body(body:Any) -> list[str]:
    if type(body) is not dict or set(body)!={"schema","app_id","release_id",
                                           "signer_id","host_abi","platforms",
                                           "modules"}:
        raise DataChipError("invalid bundle field set")
    if body["schema"]!=SCHEMA:
        raise DataChipError("unsupported application bundle version")
    for field in ("release_id","signer_id"):
        _ref(body[field])
    _ref(body["app_id"])
    if type(body["host_abi"]) is not int or body["host_abi"]!=1:
        raise DataChipError("incompatible host API version")
    platforms=body["platforms"]
    if type(platforms) is not list or len(platforms)==0 or len(platforms)>len(PLATFORMS):
        raise DataChipError("invalid application platforms")
    if any(type(v) is not str or v not in PLATFORMS for v in platforms) or len(set(platforms))!=len(platforms):
        raise DataChipError("unknown host platform")
    return _check_modules(body["modules"])


def sign_bundle(private:Ed25519PrivateKey, body:dict[str,Any]) -> dict[str,Any]:
    """Build/release-only action, not included as on-device permission."""
    _validated_body(body)
    return {"body":body,"signature":private.sign(SIGN_DOMAIN+_canon(body)).hex()}


def _sha_file(path:Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        while chunk:=f.read(1024*1024):
            h.update(chunk)
    return h.hexdigest()


def verify_bundle(signed:Any, *, trusted_bundle_keys:Mapping[str,bytes],
                  expected_app:str, expected_platform:str,
                  available_chips:Mapping[str,str|Path]) -> dict[str,Any]:
    """Verify bundle signature, dependency graph and every referenced chip.

    A signed manifest cannot grant native camera/network permissions or issue
    ENTITY rights. For grant-required modules, do not mount as usable without
    independently authenticated rights outside this method.
    """
    if type(signed) is not dict or set(signed)!={"body","signature"}:
        raise DataChipError("invalid signed bundle envelope")
    body=signed["body"]
    order=_validated_body(body)
    if body["app_id"]!=expected_app or expected_platform not in body["platforms"]:
        raise PermissionError("application/platform mismatch")
    signer=body["signer_id"]
    key=trusted_bundle_keys.get(signer) if isinstance(trusted_bundle_keys,Mapping) else None
    if type(key) is not bytes or len(key)!=32:
        raise PermissionError("bundle publisher not trusted")
    sig=signed["signature"]
    if type(sig) is not str or len(sig)!=128:
        raise PermissionError("invalid publisher signature")
    try:
        Ed25519PublicKey.from_public_bytes(key).verify(
            bytes.fromhex(sig),SIGN_DOMAIN+_canon(body))
    except (ValueError,InvalidSignature) as e:
        raise PermissionError("bundle signature invalid") from e
    source={}
    modules={item["name"]:item for item in body["modules"]}
    usable=[]
    locked=[]
    for name in order:
        item=modules[name]
        cid=item["chip_id"]
        path=available_chips.get(cid) if isinstance(available_chips,Mapping) else None
        if not isinstance(path,(str,Path)):
            raise DataChipError("referenced chip not installed")
        path=Path(path)
        if path.is_symlink() or not path.is_file():
            raise DataChipError("installed chip path missing or symlink")
        if _sha_file(path)!=item["sha256"]:
            raise DataChipError("installed chip file hash mismatch")
        if cid.startswith("edc:formula:sha256:"):
            obj=verify_formula(path)
        else:
            obj=verify_chip(path)
        if obj["chip_id"]!=cid or obj["integrity_verified"] is not True:
            raise DataChipError("installed chip ID/verification mismatch")
        # This is a mount PLAN, not permission to export bytes.
        source[name]={"chip_id":cid,"kind":item["kind"],
                      "file_sha256":item["sha256"],"data_right":item["data_right"],
                      "dependencies":item["requires"]}
        if item["data_right"]=="grant-required":
            locked.append(name)
        else:
            usable.append(name)
    return {"schema":"btg-application-databundle-resolution-v0.1",
            "app_id":body["app_id"],"release_id":body["release_id"],
            "publisher_signature_valid":True,
            "module_order":order,"modules":source,
            "available_public_modules":usable,"rights_locked_modules":locked,
            "native_code_updated":False,"os_permissions_granted":False,
            "requires_separate_rights":bool(locked)}
