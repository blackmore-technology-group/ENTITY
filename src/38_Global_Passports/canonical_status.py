from __future__ import annotations
LINEAGE="entity-origin:shawn-btg-entity@1.0"
ROOT="ent2-6eoiiztjyhmyh2tbr5psmofcduwvjledubhoiqwo6mjfoqkn6ica"
STEWARD="ent2-kkov66eoh23h3zgr4pe4njsbkayn2kxad6vfyirqvuqrty52clpa"
PROTOCOL="ent2-m3nofxtv3zwldhwuonw3h67hqjh2zambrhj4kaaulncpt4amkcua"
CANONICAL="CANONICAL_ENTITY"; DERIVED="DERIVED_FROM_ENTITY"
def policy():
 return {"lineage":LINEAGE,"root":ROOT,"steward":STEWARD,"protocol":PROTOCOL,"automatic_protocol_royalty_bps":0,"economic_participation_requires_explicit_terms":True,"protocol_origin_does_not_create_asset_entitlement":True,"protocol_origin_does_not_transfer_user_asset_ownership":True,"canonical_network_services_may_have_separate_commercial_terms":True,"removal_or_replacement_of_origin_lineage_invalidates_canonical_status":True}
def classify(c):
 c=dict(c or {}); s=c.get("status",CANONICAL)
 if s==DERIVED:return {"valid":True,"canonical":False,"status":DERIVED}
 ok=(c.get("origin_lineage_id")==LINEAGE and c.get("root_originator_entity_id")==ROOT and c.get("steward_entity_id")==STEWARD and c.get("protocol_entity_id")==PROTOCOL)
 return {"valid":bool(s==CANONICAL and ok),"canonical":bool(s==CANONICAL and ok),"status":s,"reason":None if ok else "canonical ENTITY requires immutable Shawn -> BTG -> ENTITY origin lineage"}
def verify_release_body(b):
 b=dict(b or {}); r=classify({"origin_lineage_id":b.get("origin_lineage_id"),"root_originator_entity_id":b.get("root_originator_entity_id"),"steward_entity_id":b.get("steward_entity_id"),"protocol_entity_id":b.get("protocol_entity_id")})
 if not r["valid"]:return r
 if b.get("automatic_protocol_royalty_bps")!=0:return {"valid":False,"reason":"automatic protocol royalty forbidden"}
 if b.get("economic_participation_requires_explicit_terms") is not True:return {"valid":False,"reason":"explicit econmic terms required"}
 if b.get("asset_provenance_is_separate_from_protocol_origin") is not True:return {"valid":False,"reason":"asset provenance must remain separate"}
 return r
