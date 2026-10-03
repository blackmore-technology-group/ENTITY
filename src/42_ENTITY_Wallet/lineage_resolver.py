from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import json, sqlite3

CANONICAL_LINEAGE_ID="entity-origin:shawn-btg-entity@1.0"

class WalletLineageResolver:
    """Resolve the two lineage planes used by ENTITY without collapsing them.

    protocol_lineage describes canonical ENTITY ancestry/profile context.
    asset_lineage describes actual controller/provenance relationships.
    ADAM, NIKI and BTDU are reported as capability/evidence bindings, never as
    inferred owners or economic beneficiaries.
    """
    def __init__(self,state_dir:str|Path):
        self.state=Path(state_dir)
        self.origin_path=self.state/"entity_protocol_origin.sqlite"
        self.passport_path=self.state/"entity_v3_4_global_passports.sqlite"
        self.profile_path=self.state/"entity_v3_4_global_profiles.sqlite"
        self.fabric_path=self.state/"entity_v3"/"universal_fabric.sqlite"

    def _name(self,entity_id:str|None)->str|None:
        if not entity_id: return None
        p=self.state/"identity"/"manifests"/f"{entity_id}.json"
        try:
            d=json.loads(p.read_text(encoding="utf-8"))
            return str(d.get("display_name") or d.get("aliases",[None])[0] or entity_id)
        except Exception:
            return str(entity_id)

    @staticmethod
    @contextmanager
    def _db(path:Path):
        db=sqlite3.connect(path); db.row_factory=sqlite3.Row
        try: yield db
        finally: db.close()

    def _origin(self)->dict|None:
        if not self.origin_path.exists(): return None
        try:
            with self._db(self.origin_path) as db:
                row=db.execute("SELECT body_json,body_sha256 FROM origin_chains WHERE lineage_id=?",
                               (CANONICAL_LINEAGE_ID,)).fetchone()
        except sqlite3.OperationalError:
            return None
        if not row: return None
        body=json.loads(row["body_json"]); body["body_sha256"]=row["body_sha256"]; return body

    def _passport(self,object_id:str)->dict|None:
        if not self.passport_path.exists(): return None
        try:
            with self._db(self.passport_path) as db:
                row=db.execute("""SELECT passport_id,version,body_sha256,body_json,created_at_ms
                                  FROM global_passports WHERE object_id=?
                                  ORDER BY created_at_ms DESC,passport_id DESC LIMIT 1""",
                               (str(object_id),)).fetchone()
        except sqlite3.OperationalError:
            return None
        if not row: return None
        body=json.loads(row["body_json"])
        return {**body,"body_sha256":row["body_sha256"],"created_at_ms":row["created_at_ms"]}

    def _profiles(self,refs:list[str])->list[dict]:
        if not self.profile_path.exists(): return [{"profile_ref":r} for r in refs]
        out=[]
        try:
            dbctx=self._db(self.profile_path)
            with dbctx as db:
                rows_available=True
                for ref in refs:
                    row=db.execute("""SELECT profile_ref,kind,body_json,issuer_entity_id,body_sha256
                                      FROM profile_variants WHERE profile_ref=?
                                      ORDER BY active_canonical DESC,created_at_ms DESC LIMIT 1""",(ref,)).fetchone()
                    if not row:
                        out.append({"profile_ref":ref}); continue
                    body=json.loads(row["body_json"])
                    out.append({"profile_ref":ref,"profile_id":body.get("profile_id"),"kind":row["kind"],
                                "issuer_entity_id":row["issuer_entity_id"],"issuer_name":self._name(row["issuer_entity_id"]),
                                "body_sha256":row["body_sha256"]})
        except sqlite3.OperationalError:
            return [{"profile_ref":r} for r in refs]
        return out

    def _asset_parents(self,object_id:str)->list[dict]:
        if not self.fabric_path.exists(): return []
        try:
            with self._db(self.fabric_path) as db:
                rows=db.execute("""SELECT p.edge_id,p.parent_object_id,p.relation,p.contribution_bps,
                                          o.title,o.controller_entity_id
                                   FROM provenance_edges p
                                   LEFT JOIN objects o ON o.object_id=p.parent_object_id
                                   WHERE p.child_object_id=?
                                   ORDER BY p.created_at_ms,p.edge_id""",(str(object_id),)).fetchall()
        except sqlite3.OperationalError:
            return []
        return [{**dict(r),"controller_name":self._name(r["controller_entity_id"])} for r in rows]

    @staticmethod
    def _profile_label(ref:str)->str:
        core=str(ref).split("@",1)[0].split(":")[-1]
        return {"global":"Global","robotics":"Robotics","ai":"AI","manufacturing":"Manufacturing",
                "healthcare":"Healthcare","finance":"Finance","defence-public":"Defence-public"}.get(core,core.replace("-"," ").title())

    def resolve(self,asset:dict)->dict:
        object_id=str(asset["object_id"]); controller=str(asset["controller_entity_id"])
        origin=self._origin(); passport=self._passport(object_id)
        embedded=dict((passport or {}).get("protocol_origin") or {})
        if embedded:
            root=embedded.get("root_originator_entity_id"); steward=embedded.get("steward_entity_id")
            protocol=embedded.get("protocol_entity_id"); origin_id=embedded.get("origin_lineage_id")
        elif origin:
            root=origin.get("root_originator_entity_id"); steward=origin.get("steward_entity_id")
            protocol=origin.get("protocol_entity_id"); origin_id=origin.get("lineage_id")
        else:
            root=steward=protocol=origin_id=None
        refs=list(((passport or {}).get("profile_stack") or {}).get("profile_refs") or [])
        profiles=self._profiles(refs)
        domains=[self._profile_label(x) for x in refs if "entity-profile:global@" not in x]
        primary_domain="Robotics" if "Robotics" in domains else (domains[0] if domains else None)
        composed_domains=[x for x in domains if x!=primary_domain]
        path=[self._name(root),self._name(steward),self._name(protocol),primary_domain]
        path=[x for x in path if x]
        parents=self._asset_parents(object_id)
        btdu=dict((passport or {}).get("btdu_binding") or {})
        return {
            "schema":"entity-wallet-lineage-resolution-v1",
            "protocol_lineage":{
                "lineage_id":origin_id,
                "root_originator_entity_id":root,"root_originator_name":self._name(root),
                "steward_entity_id":steward,"steward_name":self._name(steward),
                "protocol_entity_id":protocol,"protocol_name":self._name(protocol),
                "profiles":profiles,"display_path":" → ".join(path),
                "primary_domain_profile":primary_domain,"composed_domain_profiles":composed_domains,
                "profile_composition_is_not_parent_child_lineage":True,
                "passport_protocol_origin_embedded":bool(embedded),
                "resolved_from_canonical_origin_registry":bool(origin),
                "needs_passport_lineage_supersession":bool(passport and not embedded),
                "protocol_origin_is_not_asset_provenance":True,
            },
            "asset_lineage":{
                "object_id":object_id,"controller_entity_id":controller,
                "controller_name":self._name(controller),"parents":parents,
                "protocol_origin_does_not_transfer_asset_ownership":True,
            },
            "capability_bindings":{
                "BTDU":{"bound":bool(btdu),"binding":btdu or None,
                        "topology_does_not_create_ownership":True,
                        "topology_does_not_create_economic_entitlement":True},
                "ADAM":{"architecture_role":"DETERMINISTIC_EXECUTION_AND_EVIDENCE",
                        "sovereign_authority":False,"ownership_inferred":False},
                "NIKI":{"architecture_role":"BOUNDED_REASONING_AND_PROPOSALS",
                        "sovereign_authority":False,"ownership_inferred":False},
            },
            "global_passport":None if passport is None else {
                "passport_id":passport.get("passport_id"),"version":passport.get("version"),
                "body_sha256":passport.get("body_sha256"),"profile_refs":refs},
        }
