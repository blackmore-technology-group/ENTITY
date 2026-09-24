from __future__ import annotations

CORE=["ENTITY","AUTHORITY","RIGHT","EVENT","VALUE"]
KINDS={"GLOBAL","JURISDICTION","INDUSTRY","DOMAIN","PRIVACY","TRUST","DISCLOSURE"}
def _sha(v)->bool:
    s=str(v or ""); return len(s)==64 and all(c in "0123456789abcdef" for c in s)

def _stack_ok(r:dict)->bool:
    refs=r.get("profile_refs") or []; hashes=r.get("profile_hashes") or []
    return bool(refs) and "entity-profile:global@1.0" in refs and len(refs)==len(hashes) and all(_sha(x) for x in hashes) and r.get("fail_closed") is True and r.get("profile_composition_does_not_create_authority") is True and r.get("standards_mapping_is_not_normative_equivalence") is True

def _passport_ok(r:dict)->bool:
    flags=("one_passport_many_profiles","profile_composition_does_not_create_authority","standards_mapping_is_not_normative_equivalence","evidence_does_not_establish_objective_truth","legal_effect_is_deployment_specific","underlying_information_remains_nonrival")
    econ=r.get("economic_state") or {}; mappings=r.get("standards_mappings") or []
    return r.get("core_primitives")==CORE and bool(r.get("rights_passport_id")) and _sha(r.get("rights_passport_sha256")) and isinstance(r.get("profile_stack"),dict) and _stack_ok(r["profile_stack"]) and all(r.get(x) is True for x in flags) and all(m.get("normative_equivalence_claimed") is False for m in mappings) and int(econ.get("amount_units",-1))>=0 and econ.get("market_observation_is_not_accounting_fair_value") is True

def validate_global_passport_record(r:dict)->bool:
    try:
        schema=r.get("schema")
        if schema=="entity-v3-global-passport-profile-status-v1":
            return r.get("core_primitives")==CORE and r.get("core_semantics_changed") is False and r.get("market_engine_preserved") is True and r.get("one_passport_many_profiles") is True and r.get("evidence_truth_boundary_preserved") is True
        if schema=="entity-v3-global-profile-v1":
            return bool(r.get("profile_ref")) and r.get("kind") in KINDS and _sha(r.get("schema_sha256")) and r.get("profile_is_not_authority") is True and r.get("standards_mapping_is_not_normative_equivalence") is True and ("DEFENCE" not in str(r.get("profile_id","")).upper() or r.get("public_unclassified") is True)
        if schema=="entity-v3-profile-stack-resolution-v1": return _stack_ok(r)
        if schema=="entity-v3-global-passport-v1": return _passport_ok(r)
        if schema=="entity-v3-continuous-ingest-result-v1":
            return int(r.get("files",-1))>=0 and _sha(r.get("inventory_sha256")) and r.get("content_addressed") is True and r.get("custody_is_not_authority") is True and r.get("economic_value_invented") is False
        return False
    except Exception: return False
