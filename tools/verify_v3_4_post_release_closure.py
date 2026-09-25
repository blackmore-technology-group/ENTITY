from __future__ import annotations
import hashlib, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
REPORT=ROOT/"docs/qualification/ENTITY_V3_4_0_POST_RELEASE_RECURSIVE_CLOSURE_2026-09-24.json"
CATALOG=ROOT/"docs/qualification/ENTITY_V3_4_0_POST_RELEASE_RECURSIVE_CLOSURE_CATALOG_2026-09-24.json"
EXPECTED_COMMIT="2db5bff64507b8d67642122a5ff2fc73dfef9152"
EXPECTED_ROOT="4feb51a4bd0d958b7beb3eddbe9fd78678b7c31c2a4fe3d6cf7d9f4d87aa6e06"

def sha(data:bytes)->str: return hashlib.sha256(data).hexdigest()

def main():
    report=json.loads(REPORT.read_text(encoding="utf-8")); catalog=json.loads(CATALOG.read_text(encoding="utf-8")); errors=[]
    if report.get("status")!="PASS" or report.get("target",{}).get("commit")!=EXPECTED_COMMIT: errors.append("target")
    roots=report.get("roots",{})
    if roots.get("frozen_constituent_root_sha256")!=EXPECTED_ROOT or roots.get("entity_ingested_constituent_root_sha256")!=EXPECTED_ROOT: errors.append("constituent_root")
    records=list(catalog.get("records") or []); constituents=[r for r in records if r.get("category")!="closure_anchor"]
    material="\n".join(f"{r['content_sha256']}  {r['logical_path']}" for r in constituents).encode()
    if len(records)!=1041 or len(constituents)!=1040 or sha(material)!=EXPECTED_ROOT: errors.append("catalog")
    if len({r["logical_path"] for r in records})!=len(records): errors.append("duplicate_paths")
    cov=report.get("coverage",{}); counts=report.get("entity_native_records",{}); recovery=report.get("destructive_recovery",{})
    if cov.get("constituents")!=1040 or cov.get("total_ingested_objects")!=1041: errors.append("coverage")
    for key in ("objects","rights","values","evidence_objects","rights_passports","global_passports"):
        if counts.get(key)!=1041: errors.append("count_"+key)
    if counts.get("provenance_edges")!=1040: errors.append("count_provenance")
    if not all(recovery.get(k) is True for k in ("performed","identical_state_tree","identical_sqlite_semantics","identical_content_vault","all_objects_evidence_rights_passports_global_passports_and_vault_bytes_reverified")): errors.append("recovery")
    if roots.get("state_tree_before_destruction")!=roots.get("state_tree_after_recovery"): errors.append("state_root")
    if roots.get("sqlite_semantic_before_destruction")!=roots.get("sqlite_semantic_after_recovery"): errors.append("semantic_root")
    if roots.get("content_vault_before_destruction")!=roots.get("content_vault_after_recovery"): errors.append("vault_root")
    boundary=report.get("claim_boundary",{})
    if boundary.get("btg_controlled_evidence_is_not_independent_third_party_validation") is not True: errors.append("claim_boundary")
    if any(boundary.get(k) is True for k in ("objective_external_truth_claimed","legal_or_regulatory_compliance_claimed","independent_security_review_claimed","market_adoption_or_liquidity_claimed","accounting_fair_value_claimed","custody_is_authority","economic_value_invented")): errors.append("overclaim")
    result={"valid":not errors,"errors":errors,"records":len(records),"constituents":len(constituents),"constituent_root_sha256":sha(material),"target_commit":report.get("target",{}).get("commit")}
    print(json.dumps(result,indent=2,sort_keys=True)); return 0 if not errors else 2

if __name__=="__main__": raise SystemExit(main())
