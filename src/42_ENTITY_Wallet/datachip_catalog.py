"""Fail-closed read-only DCO -> typed DataChip reference adapters for ENTITY.

The authenticated wallet snapshot is a discovery boundary, not a runtime
licence or signed issuer grant. A module emits entity.asset.reference, never
entity.content.verified or executable code. Real EDCF verification, passport
grants, revocation and host deployment remain separate.
"""
from __future__ import annotations
from hashlib import sha256
from typing import Any
import re

SCHEMA="entity-datachip-interface-v0.1"
OID=re.compile(r"^[A-Za-z][A-Za-z0-9_.:/@-]{0,130}$")
HASH=re.compile(r"^[0-9a-f]{64}$")
MAX_ASSETS=10000

class CatalogError(ValueError):pass

def owned_dco_catalog(snapshot: dict[str,Any], wallet_entity_id:str) -> list[dict]:
    if not isinstance(wallet_entity_id,str) or not OID.fullmatch(wallet_entity_id):
        raise CatalogError("unrecognized wallet identity")
    if not isinstance(snapshot,dict):
        raise CatalogError("wallet snapshot unavailable")
    wallet=snapshot.get("wallet")
    if not isinstance(wallet,dict) or wallet.get("owner_entity_id")!=wallet_entity_id:
        raise CatalogError("snapshot owner is not the active wallet")
    assets=snapshot.get("assets")
    if not isinstance(assets,list) or len(assets)>MAX_ASSETS:
        raise CatalogError("unbounded or missing wallet DCO collection")
    result=[]
    seen=set()
    for row in assets:
        if not isinstance(row,dict):
            raise CatalogError("malformed digital asset")
        oid=row.get("object_id")
        if not isinstance(oid,str) or not OID.fullmatch(oid):
            raise CatalogError("malformed DCO object identity")
        if oid in seen:raise CatalogError("duplicate wallet object")
        seen.add(oid)
        if row.get("controller_entity_id")!=wallet_entity_id:
            raise CatalogError("mixed-controller wallet asset list")
        if row.get("status")!="ACTIVE":
            raise CatalogError("inactive DCO in active wallet snapshot")
        descriptor=row.get("descriptor")
        if not isinstance(descriptor,dict) or descriptor.get("digital_commodity") is not True:
            raise CatalogError("non-DCO in digital asset snapshot")
        content_sha=row.get("content_sha256")
        if not isinstance(content_sha,str) or not HASH.fullmatch(content_sha):
            raise CatalogError("missing authoritative asset content hash")
        title=row.get("title")
        if not isinstance(title,str) or not title.strip():
            raise CatalogError("untitled DCO")
        item={"object_id":oid,
              "title":title.strip()[:90],
              "content_sha256":content_sha,
              "controller_entity_id":wallet_entity_id,
              "asset_kind":str(row.get("object_type") or "UNKNOWN")[:40],
              "commodity_class":str(row.get("commodity_class") or "UNCLASSIFIED")[:60],
              "asset_reference_only":True,
              "content_chip_verified":False,
              "execution_authorized":False,
              "rights_grant_issued":False}
        result.append(item)
    return sorted(result,key=lambda d:(d["title"].casefold(),d["object_id"]))

def interface_for_dco(item:dict) -> dict:
    if not isinstance(item,dict) or item.get("asset_reference_only") is not True:
        raise CatalogError("only wallet-scoped DCO reference can be imported")
    oid=item.get("object_id","")
    if not isinstance(oid,str) or not OID.fullmatch(oid):
        raise CatalogError("bad DCO identifier")
    mid="entity.wallet.dco."+sha256(oid.encode("utf-8")).hexdigest()[:32]
    return {
        "schema":SCHEMA,"module_id":mid,
        "name":("DCO · "+str(item["title"]))[:80],
        "version":"0.1.0","kind":"source",
        "inputs":[],
        "outputs":[{"name":"asset_ref","type":"entity.asset.reference","required":False}],
    }

def binding_for_dco(item:dict) ->dict:
    """Optional NON-AUTHORIZING provenance evidence for UI, not a grant."""
    manifest=interface_for_dco(item)
    return {"module_id":manifest["module_id"],"object_id":item["object_id"],
            "content_sha256":item["content_sha256"],"controller_entity_id":item["controller_entity_id"],
            "binding_kind":"DCO_REFERENCE_ONLY",
            "issuer_authenticated":False,"content_chip_verified":False,
            "rights_authorized":False}
