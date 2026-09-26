from __future__ import annotations
ALLOWED_ORIGINS={'DIRECT_OBSERVATION','ENTITY_ASSERTION','COUNTERPARTY_ATTESTATION','EXTERNAL_AUTHORITATIVE_RECORD','DERIVED_INFERENCE','UNKNOWN'}
class ArProjectionAuthority:
    """Read-only AR presentation layer over BSIE/ENTITY state; never authoritative for rights or mutation."""
    @staticmethod
    def project(world_projection:dict,*,classification:str='PUBLIC',allow_sensitive:bool=False,parent_provenance:str|None=None)->dict:
        src=dict(world_projection or {}); origin=str(src.get('evidence_origin') or 'UNKNOWN').upper()
        if origin not in ALLOWED_ORIGINS: origin='UNKNOWN'
        state=src.get('state')
        if str(classification).upper() in {'PRIVATE','RESTRICTED'} and not allow_sensitive: state={'redacted':True}
        return {'schema':'entity-ar-projection-v1','world_id':src.get('world_id'),'state':state,'evidence_origin':origin,'parent_provenance':parent_provenance or src.get('provenance_ref'),'read_only':True,'authoritative_mutation_allowed':False,'rights_inferred':False,'classification':str(classification).upper()}
    @staticmethod
    def classify_ai(label:str,confidence:float)->dict:
        return {'label':str(label),'confidence':max(0.0,min(1.0,float(confidence))),'evidence_origin':'DERIVED_INFERENCE','verified_fact':False}
    def status(self): return {'ready':True,'read_only':True,'sensitive_redaction':True,'ai_classification_is_inference':True,'authority_bypass':False}

def niki_accept_overlay_layer_v1(*,projection:dict)->dict:
    if projection.get('authoritative_mutation_allowed') is not False: raise PermissionError('AR overlay cannot carry mutation authority')
    return dict(projection)
