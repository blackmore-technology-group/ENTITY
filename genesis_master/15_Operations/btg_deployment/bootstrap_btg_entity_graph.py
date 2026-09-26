from __future__ import annotations
from pathlib import Path
import hashlib, importlib.util, json, sqlite3, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
STATE=Path(r"<LOCAL_DRIVE>/BTG_ENTITY_PRODUCTION_STATE")
STATE.mkdir(parents=True,exist_ok=True)

def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def _sha(v):
    raw=json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

IM=_load("btg_prod_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
DM=_load("btg_prod_domain",ROOT/"22_Sovereign_Domain"/"core"/"canonical_domain.py")
SM=_load("btg_prod_sovereign",ROOT/"04_Entity_Registry"/"relationships"/"canonical_sovereign_authority.py")
identity=IM.EntityIdentityVault(STATE)
domains=DM.EntityDomainAuthority(STATE,identity)
sovereign=SM.SovereignAuthorityRegistry(STATE,identity)

def get_or_create(display_name,entity_type,alias,metadata=None):
    alias=str(alias).lower()
    for item in identity.list_local():
        if alias in {str(x).lower() for x in (item.get("aliases") or [])}:
            return item
    return identity.create(display_name,entity_type,aliases=[alias],metadata=dict(metadata or {}))

def ensure_domain(entity_id,alias):
    with sqlite3.connect(domains.path) as db:
        row=db.execute("SELECT domain_id FROM domains WHERE entity_id=? AND status='ACTIVE' ORDER BY created_at_ms LIMIT 1",(entity_id,)).fetchone()
    if row:
        domain=domains.get_domain(row[0]); claim=domains.current_name_claim(row[0])
        if not claim or claim.get("normalized_name")!=alias:
            claim=domains.claim_name(entity_id,row[0],alias,evidence={"profile":"BTG_PRODUCTION_ENTITY_GRAPH_v1"})
        return domain,claim
    created=domains.create_domain(entity_id,namespace="entity",requested_name=alias)
    return domains.get_domain(created["domain_id"]),created.get("name_claim")

def ensure_relationship(entity_id,party_ref,relationship_type,scope):
    active=sovereign.active_relationships(entity_id,party_ref)
    for item in active:
        if item["relationship_type"]==relationship_type and item.get("scope")==scope:
            return item
    return sovereign.grant_relationship(entity_id,party_ref,relationship_type,scope=scope,
        evidence_origin="ENTITY_ASSERTION",evidence={"profile":"BTG_PRODUCTION_ENTITY_GRAPH_v1","legal_truth_not_inferred":True})

SPECS=[
    ("shawn","Shawn Blackmore","person","shawn.blackmore.entity",{"role":"BTG founder/developer","rights_status":"internal asserted relationship only"}),
    ("nicole","Nicole Best","person","nicole.best.entity",{"role":"Boundarys Best creator/operator","rights_status":"internal asserted relationship only"}),
    ("btg","Blackmore Technology Group Limited","business","btg.entity",{"role":"BTG organization"}),
    ("entity","ENTITY","system","entity.entity",{"product":"ENTITY sovereign data/economic infrastructure"}),
    ("huntar","HUNTAR","application","huntar.entity",{"product":"HUNTAR"}),
    ("searchar","SEARCHAR","application","searchar.entity",{"product":"SEARCHAR"}),
    ("hikear","HIKEAR","application","hikear.entity",{"product":"HIKEAR"}),
    ("niki","NIKI","system","niki.entity",{"product":"Neural Integrated Knowledge Intelligence"}),
    ("bsie","BSIE","system","bsie.entity",{"product":"Blackmore Spatial Intelligence Engine"}),
    ("adam","ADAM","system","adam.entity",{"product":"Atomic Data and Memory"}),
    ("becp","BECP","system","becp.entity",{"product":"Blackmore Engineering Control Platform"}),
    ("boundarys","Boundarys Best","business","boundarys.best.entity",{"role":"Boundarys Best business/data principal"}),
    ("soapstudio","Boundarys Best Soap Studio","application","soapstudio.boundarys.best.entity",{"product":"WildByNatureSoapStudio"}),
    ("formulations","Boundarys Best Formulations","project","formulations.boundarys.best.entity",{"role":"Boundarys Best formulation data collection"}),
    ("products","Boundarys Best Products","project","products.boundarys.best.entity",{"role":"Boundarys Best product data collection"}),
]

records={}
for key,name,kind,alias,meta in SPECS:
    manifest=get_or_create(name,kind,alias,{**meta,"deployment_profile":"BTG_PRODUCTION_ENTITY_GRAPH_v1"})
    domain,claim=ensure_domain(manifest["entity_id"],alias)
    binding=_sha({"namespace":"entity","normalized_name":alias,"entity_root":manifest["entity_id"]})
    records[key]={"display_name":name,"alias":alias,"entity_id":manifest["entity_id"],"domain_id":domain["domain_id"],
                  "alias_binding_sha256":binding,"collision_safe_display":f"{alias}~{binding[:12]}"}

# Internal authority/control assertions. These are signed operational relationships, not legal adjudications.
ensure_relationship(records["btg"]["entity_id"],records["shawn"]["entity_id"],"GOVERNANCE_AUTHORITY",
                    {"btg_governance":True,"legal_ownership_not_adjudicated":True})
ensure_relationship(records["boundarys"]["entity_id"],records["nicole"]["entity_id"],"GOVERNANCE_AUTHORITY",
                    {"boundarys_best_governance":True,"legal_ownership_not_adjudicated":True})
ensure_relationship(records["boundarys"]["entity_id"],records["nicole"]["entity_id"],"SOVEREIGN_AUTHORITY",
                    {"business_data_control":True,"formulation_authority":True,"legal_ownership_not_adjudicated":True})

for key in ["entity","huntar","searchar","hikear","niki","bsie","adam","becp","soapstudio"]:
    ensure_relationship(records[key]["entity_id"],records["btg"]["entity_id"],"SOVEREIGN_AUTHORITY",
                        {"software_application_control":True,"data_ownership_not_implied":True})
    ensure_relationship(records[key]["entity_id"],records["btg"]["entity_id"],"CREATORSHIP",
                        {"software_product_relationship":True,"legal_ownership_not_adjudicated":True})

# Boundarys Best receives application processing authority without transferring software sovereignty or data rights to BTG.
ensure_relationship(records["soapstudio"]["entity_id"],records["boundarys"]["entity_id"],"PROCESSING_AUTHORITY",
                    {"business_formulation_processing":True,"software_control_remains_separate":True})
for key in ["formulations","products"]:
    ensure_relationship(records[key]["entity_id"],records["boundarys"]["entity_id"],"SOVEREIGN_AUTHORITY",
                        {"boundarys_best_collection_control":True,"legal_ownership_not_adjudicated":True})
    ensure_relationship(records[key]["entity_id"],records["nicole"]["entity_id"],"CREATORSHIP",
                        {"collection_originator_relationship":True,"individual_asset_rights_remain_separate":True})

profile={
  "schema":"btg-entity-deployment-profile-v1",
  "generated_at_ms":int(time.time()*1000),
  "state_root":str(STATE),
  "entities":records,
  "authority_boundary":{
      "platform_operator":"btg.entity",
      "entity_platform":"entity.entity",
      "open_source_protocol_remains_provider_neutral":True,
      "btg_control_does_not_transfer_user_data_rights":True,
      "registration_is_not_legal_ownership":True},
  "data_controller_defaults":{
      "huntar.entity":"USER_ENTITY_FOR_USER_GENERATED_DATA",
      "searchar.entity":"USER_ENTITY_FOR_USER_GENERATED_DATA",
      "hikear.entity":"USER_ENTITY_FOR_USER_GENERATED_DATA",
      "niki.entity":"PRESERVE_SOURCE_CONTROLLER_THROUGH_DERIVATION",
      "soapstudio.boundarys.best.entity":"boundarys.best.entity",
      "formulations.boundarys.best.entity":"boundarys.best.entity",
      "products.boundarys.best.entity":"boundarys.best.entity",
      "btg_software_assets":"btg.entity"},
  "lineage_rule":"Every derived asset preserves originating Entity IDs, producer application Entity, controller Entity, source/parent asset IDs, provenance and rights/consent state.",
  "economic_rule":"Economic contribution may be recorded only after canonical rights/consent/licence/usage/economic controls authorize the transition; data creation alone does not manufacture value or ownership."
}
out=STATE/"BTG_ENTITY_GRAPH.json"
out.write_text(json.dumps(profile,indent=2,sort_keys=True)+"\n",encoding="utf-8")
file_sha=hashlib.sha256(out.read_bytes()).hexdigest()
(STATE/"BTG_ENTITY_GRAPH.json.sha256").write_text(file_sha+"  BTG_ENTITY_GRAPH.json\n",encoding="utf-8")
print(json.dumps({"status":"READY","state_root":str(STATE),"entities":records,
                  "graph_manifest":str(out),"graph_manifest_sha256":file_sha},indent=2))
