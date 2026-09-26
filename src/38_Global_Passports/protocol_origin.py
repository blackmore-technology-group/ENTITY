from __future__ import annotations

import importlib.util as _entity_ilu
from pathlib import Path as _EntityPath
_entity_cs_spec=_entity_ilu.spec_from_file_location("_entity_canonical_status",_EntityPath(__file__).with_name("canonical_status.py"))
_entity_canonical_status=_entity_ilu.module_from_spec(_entity_cs_spec)
_entity_cs_spec.loader.exec_module(_entity_canonical_status)
from pathlib import Path
from typing import Any
import hashlib, json, re, sqlite3

SHA1_RE=re.compile(r"^[0-9a-f]{40}$")

def canon(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()

def digest(v:Any)->str:
    return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else canon(v)).hexdigest()

class ProtocolOriginRegistry:
    """Verified protocol-origin lineage kept separate from user asset provenance."""
    def __init__(self,root:str|Path,identity):
        self.path=Path(root)/"entity_protocol_origin.sqlite"
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.identity=identity
        self.default_release_ref=None
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS origin_chains(
            lineage_id TEXT PRIMARY KEY, body_sha256 TEXT NOT NULL, body_json TEXT NOT NULL,
            signatures_json TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS release_origins(
            release_ref TEXT PRIMARY KEY, release_tag TEXT NOT NULL, release_commit_sha1 TEXT NOT NULL,
            release_tree_sha1 TEXT NOT NULL, body_sha256 TEXT NOT NULL, body_json TEXT NOT NULL,
            signature_json TEXT NOT NULL)""")
    def verify_origin(self,record:dict)->dict:
        try:
            body=dict(record["body"]); sigs=dict(record["signatures"])
            if body.get("schema")!="entity-protocol-origin-lineage-v1": raise ValueError("schema")
            if record.get("body_sha256")!=digest(body): raise ValueError("hash")
            if body.get("asset_provenance_is_separate_from_protocol_origin") is not True: raise ValueError("asset boundary")
            if body.get("protocol_origin_does_not_transfer_authority") is not True: raise ValueError("authority boundary")
            if body.get("protocol_origin_does_not_transfer_user_asset_ownership") is not True: raise ValueError("ownership boundary")
            if body.get("economic_participation_requires_explicit_terms") is not True: raise ValueError("economic boundary")
            if int(body.get("automatic_protocol_royalty_bps",-1))!=0: raise ValueError("hidden protocol royalty")
            roles={"root_originator":"root_originator_entity_id","steward":"steward_entity_id","protocol":"protocol_entity_id"}
            for role,field in roles.items():
                eid=str(body[field]); manifest=self.identity.load_manifest(eid)
                if not self.identity.verify_signature(manifest,body,dict(sigs.get(role) or {})): raise ValueError("signature:"+role)
            rels=list(body.get("relations") or [])
            if len(rels)!=2: raise ValueError("canonical chain length")
            if rels[0].get("from_entity_id")!=body["root_originator_entity_id"] or rels[0].get("to_entity_id")!=body["steward_entity_id"]: raise ValueError("root relation")
            if rels[1].get("from_entity_id")!=body["steward_entity_id"] or rels[1].get("to_entity_id")!=body["protocol_entity_id"]: raise ValueError("protocol relation")
            return {"valid":True,"lineage_id":body["lineage_id"],"body_sha256":record["body_sha256"]}
        except Exception as exc:
            return {"valid":False,"reason":type(exc).__name__}
    def verify_release(self,record:dict)->dict:
        _canonical_check=_entity_canonical_status.verify_release_body(dict(record.get("body") or {}))
        if not _canonical_check.get("valid"):
            return {"valid":False,"reason":_canonical_check.get("reason","canonical status failure")}
        try:
            body=dict(record["body"])
            if body.get("schema")!="entity-protocol-release-origin-v1": raise ValueError("schema")
            if record.get("body_sha256")!=digest(body): raise ValueError("hash")
            if not SHA1_RE.fullmatch(str(body.get("release_commit_sha1") or "")): raise ValueError("commit")
            if not SHA1_RE.fullmatch(str(body.get("release_tree_sha1") or "")): raise ValueError("tree")
            if body.get("asset_provenance_is_separate_from_protocol_origin") is not True: raise ValueError("asset boundary")
            if body.get("economic_participation_requires_explicit_terms") is not True: raise ValueError("economic boundary")
            if int(body.get("automatic_protocol_royalty_bps",-1))!=0: raise ValueError("hidden protocol royalty")
            origin=self.get_origin(body["origin_lineage_id"])
            if origin["body_sha256"]!=body["origin_lineage_sha256"]: raise ValueError("origin hash")
            if origin["body"]["protocol_entity_id"]!=body["protocol_entity_id"]: raise ValueError("protocol id")
            manifest=self.identity.load_manifest(body["protocol_entity_id"])
            if not self.identity.verify_signature(manifest,body,dict(record.get("signature") or {})): raise ValueError("signature")
            return {"valid":True,"release_ref":body["release_ref"],"body_sha256":record["body_sha256"]}
        except Exception as exc:
            return {"valid":False,"reason":type(exc).__name__}

    def get_origin(self,lineage_id:str)->dict:
        with sqlite3.connect(self.path) as db:
            db.row_factory=sqlite3.Row; row=db.execute("SELECT * FROM origin_chains WHERE lineage_id=?",(str(lineage_id),)).fetchone()
        if not row: raise KeyError("origin lineage missing")
        return {"body":json.loads(row["body_json"]),"body_sha256":row["body_sha256"],"signatures":json.loads(row["signatures_json"])}
    def get_release(self,release_ref:str)->dict:
        with sqlite3.connect(self.path) as db:
            db.row_factory=sqlite3.Row; row=db.execute("SELECT * FROM release_origins WHERE release_ref=?",(str(release_ref),)).fetchone()
        if not row: raise KeyError("release origin missing")
        return {"body":json.loads(row["body_json"]),"body_sha256":row["body_sha256"],"signature":json.loads(row["signature_json"])}

    def import_origin(self,record:dict)->dict:
        check=self.verify_origin(record)
        if not check["valid"]: raise ValueError("invalid origin lineage: "+check.get("reason","unknown"))
        body=record["body"]
        with sqlite3.connect(self.path) as db:
            prior=db.execute("SELECT body_sha256 FROM origin_chains WHERE lineage_id=?",(body["lineage_id"],)).fetchone()
            if prior and prior[0]!=record["body_sha256"]: raise ValueError("origin lineage conflict")
            db.execute("INSERT OR IGNORE INTO origin_chains VALUES(?,?,?,?)",(body["lineage_id"],record["body_sha256"],json.dumps(body,sort_keys=True),json.dumps(record["signatures"],sort_keys=True)))
        return self.get_origin(body["lineage_id"])

    def import_release(self,record:dict)->dict:
        check=self.verify_release(record)
        if not check["valid"]: raise ValueError("invalid release origin: "+check.get("reason","unknown"))
        body=record["body"]
        with sqlite3.connect(self.path) as db:
            prior=db.execute("SELECT body_sha256 FROM release_origins WHERE release_ref=?",(body["release_ref"],)).fetchone()
            if prior and prior[0]!=record["body_sha256"]: raise ValueError("release origin conflict")
            db.execute("INSERT OR IGNORE INTO release_origins VALUES(?,?,?,?,?,?,?)",(body["release_ref"],body["release_tag"],body["release_commit_sha1"],body["release_tree_sha1"],record["body_sha256"],json.dumps(body,sort_keys=True),json.dumps(record["signature"],sort_keys=True)))
        return self.get_release(body["release_ref"])

    def install_current_release(self,record:dict,expected_tag:str)->dict:
        imported=self.import_release(record); body=imported["body"]
        if body.get("release_tag")!=str(expected_tag): raise ValueError("current release tag mismatch")
        expected_ref="entity-release:"+str(expected_tag)
        if body.get("release_ref")!=expected_ref: raise ValueError("current release ref mismatch")
        self.default_release_ref=expected_ref
        return {"schema":"entity-current-release-origin-install-result-v1","release_ref":expected_ref,
                "release_tag":str(expected_tag),"body_sha256":imported["body_sha256"],
                "release_commit_sha1":body["release_commit_sha1"],"release_tree_sha1":body["release_tree_sha1"],
                "current_release_origin_verified":True}

    def install_bundle(self,bundle:dict,profile_registry=None)->dict:
        if bundle.get("schema")!="entity-protocol-origin-bundle-v1": raise ValueError("origin bundle schema")
        supplied=bundle.get("bundle_sha256"); unsigned=dict(bundle); unsigned.pop("bundle_sha256",None)
        if supplied!=digest(unsigned): raise ValueError("origin bundle hash mismatch")
        manifests=dict(bundle.get("public_manifests") or {})
        for role in ("root_originator","steward","protocol"):
            if role not in manifests: raise ValueError("missing public manifest: "+role)
            self.identity.import_public_manifest(manifests[role])
        origin=self.import_origin(dict(bundle["origin_chain"]))
        imported_profiles=0; retained_profiles=0; rebound_profiles=0
        if profile_registry is not None:
            protocol_entity_id=origin["body"]["protocol_entity_id"]
            for profile in bundle.get("canonical_profiles") or []:
                profile=dict(profile)
                if profile.get("issuer_entity_id")!=protocol_entity_id: raise ValueError("canonical profile issuer is not ENTITY protocol identity")
                try: prior=profile_registry.get(profile["profile_ref"])
                except KeyError: prior=None
                active=profile_registry.import_signed(profile,allow_semantic_rebind=True)
                if prior is None: imported_profiles+=1
                elif prior["body_sha256"]==active["body_sha256"]: retained_profiles+=1
                else: rebound_profiles+=1
        releases=[self.import_release(dict(r)) for r in bundle.get("release_origins") or []]
        default_ref=str(bundle.get("default_release_ref") or "")
        if default_ref and default_ref not in {r["body"]["release_ref"] for r in releases}: raise ValueError("default release origin missing")
        self.default_release_ref=default_ref or None
        return {"schema":"entity-protocol-origin-install-result-v1","bundle_sha256":supplied,
                "origin_lineage_id":origin["body"]["lineage_id"],"origin_lineage_sha256":origin["body_sha256"],
                "release_origins":len(releases),"canonical_profiles":len(bundle.get("canonical_profiles") or []),
                "canonical_profiles_imported":imported_profiles,"semantically_identical_profiles_retained":retained_profiles,
                "legacy_profiles_rebound_to_canonical_entity_issuer":rebound_profiles,
                "default_release_ref":default_ref,"user_asset_provenance_remains_independent":True,
                "automatic_protocol_royalty_bps":0}

    def passport_binding(self,release_ref:str)->dict:
        rel=self.get_release(release_ref); body=rel["body"]
        return {"release_ref":body["release_ref"],"release_tag":body["release_tag"],
                "release_commit_sha1":body["release_commit_sha1"],"release_tree_sha1":body["release_tree_sha1"],
                "origin_lineage_id":body["origin_lineage_id"],"origin_lineage_sha256":body["origin_lineage_sha256"],
                "protocol_entity_id":body["protocol_entity_id"],"steward_entity_id":body["steward_entity_id"],
                "root_originator_entity_id":body["root_originator_entity_id"],
                "asset_provenance_is_separate_from_protocol_origin":True,
                "protocol_origin_does_not_transfer_authority":True,
                "protocol_origin_does_not_transfer_user_asset_ownership":True,
                "economic_participation_requires_explicit_terms":True,"automatic_protocol_royalty_bps":0}
