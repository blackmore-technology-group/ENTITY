from __future__ import annotations
from pathlib import Path
import importlib.util, os

ROOT=Path(__file__).resolve().parents[2]
def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

class DataUniverseProjection:
    """Read-only, minimum-necessary projection composed from canonical registries."""
    def __init__(self,state_dir:str|Path,identity):
        self.state=Path(state_dir); self.identity=identity
        am=_load("du_assets",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py")
        rm=_load("du_rights",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
        pm=_load("du_prov",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py")
        self.assets=am.CanonicalAssetRegistry(self.state,identity); self.rights=rm.RightsClaimsGraph(self.state,identity); self.prov=pm.AssetProvenanceGraph(self.state,identity)
    def project(self,entity_id:str)->dict:
        rows=[]
        for a in self.assets.list_for_controller(entity_id):
            claims=self.rights.claims_for_asset(a["asset_id"])
            lineage=self.prov.lineage(a["asset_id"])
            rows.append({"asset_id":a["asset_id"],"content_sha256":a["content_sha256"],"status":a.get("status"),"classification":a.get("classification"),"rights_claim_count":len(claims),"provenance_recorded":bool(lineage.get("binding")),"ownership_not_inferred":True})
        return {"schema":"entity-data-universe-projection-v1","entity_id":entity_id,"assets":rows,"raw_vault_content_exposed":False,"owner_field_synthesized":False,"minimum_necessary":True}

def niki_project_data_summary_v1(*,entity_id:str)->dict:
    im=_load("du_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    state=Path(os.environ.get("ENTITY_CANONICAL_CORE_STATE",str(ROOT/"01_Core_Runtime"/"runtime_state")))
    return DataUniverseProjection(state,im.EntityIdentityVault(state)).project(str(entity_id))
