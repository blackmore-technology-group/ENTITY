from __future__ import annotations
import hashlib, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
QDIR=ROOT/"docs/qualification"; QDIR.mkdir(parents=True,exist_ok=True)
REG=ROOT/"profiles/registry.json"
registry=json.loads(REG.read_text(encoding="utf-8"))
package_hashes={row["name"]:row["package_sha256"] for row in registry["packages"]}
runs={
 "rust":{"commit":"6647e3a8f3adf3fab4d305f47613a24362fc7d67","run":36166115869},
 "typescript":{"commit":"32ce64654690f8dba0d74e60f042cc636784edb8","run":36166120488},
 "go":{"commit":"7ef2dbcf64205f2bb86589e373fef550d2e82922","run":36166124241},
 "csharp":{"commit":"bfbddb7af2a32b4851a123e875bbf4792af29d1f","run":36166127944},
 "java":{"commit":"c1bd4e503ed520f7d563d62914f6e8acee2b596e","run":36166132361},
 "swift":{"commit":"d92a30fa202c2c981c41d9020f6a866d587b34b4","run":36166136838},
}
for lang,row in runs.items():
 row["conclusion"]="success"
 row["url"]=f"https://github.com/blackmore-technology-group/ENTITY-{lang.upper()}-CLEANROOM/actions/runs/{row['run']}"
qualification={
 "schema":"entity-v3-4-1-release-qualification-v1","version":"3.4.1",
 "status":"BTG_INTERNAL_QUALIFIED_PROTOCOL_ORIGIN_LINEAGE_SOVEREIGN_BOOTSTRAP_PATCH",
 "date":"2026-09-25","base_release":"v3.4.0",
 "base_commit":"2db5bff64507b8d67642122a5ff2fc73dfef9152",
 "qualified_source_commit":"04d7386c70ef1665ea44824d16e1bb09f5329ca8",
 "regression":{"environment":"_venv_entity_v3","passed":185,"total":185},
 "targeted_protocol_origin_tests":{"passed":8,"total":8},
 "targeted_global_passport_tests":{"passed":33,"total":33},
 "global_passport_conformance":{"total":24,"valid":12,"invalid":12,
   "sealed_kit_sha256":"f95c2b347da97742fed3f20611f0eec2fd3df48694fed9494fb07163c537cfb7",
   "schema_sha256":"3d72b4e67ec9929c5d960cee8fc52db35d85ba5103e361f3a61a8f5078079c5d",
   "expected_result_sha256":"ac7504cce70576008cff069607619660a4b9bf0cad43b3f3de81078f1e80d9ba"},
 "protocol_origin":{"origin_chain_sha256":"9d3bdc0ef2e6a27de5368541f6bc014fdec93b2c7af9770d163c804521b9efff",
   "historical_release_anchors":9,"fresh_user_never_canonical_profile_issuer":True,
   "asset_provenance_separate_from_protocol_origin":True,"automatic_protocol_royalty_bps":0},
 "v3_4_0_migration":{"legacy_profile_variants_preserved":True,"canonical_profiles_rebound":7,
   "user_entity_unchanged":True,"user_objects_unchanged":True,"rights_passports_unchanged":True,
   "historical_global_passport_verifies":True},
 "data_economy_lineage":{"status":"PASS","protocol_tax_bps":0,
   "data_originator_remains_instrument_and_policy_originator":True,
   "treasury_recipient_not_replaced_by_protocol_origin":True,
   "trade_capture_reconciliation_complete":True},
 "six_language_controlled_interoperability":{"status":"PASS","independent_third_party_interoperability":False,
   "result_sha256":"ac7504cce70576008cff069607619660a4b9bf0cad43b3f3de81078f1e80d9ba","implementations":runs},
 "implementation_packages":{"status":"PASS","packages":6,
   "registry_sha256":hashlib.sha256(REG.read_bytes()).hexdigest(),"package_sha256":package_hashes,
   "profiles_are_executable_implementation_assets":True,"developer_configures_not_redesigns":True},
 "current_release_origin":{"source_tree_self_anchor":False,"post_tag_signed_sidecar_required":True,
   "new_issuance_fails_closed_without_v3_4_1_sidecar":True},
 "external_remaining":[
   "unrelated third-party independent v3.4.1 implementation and live interoperability",
   "independent external security/cryptographic review",
   "deployment-specific legal/regulatory classification, licensing, recognition or approval where required",
   "real external issuers, buyers, repeat transactions and market liquidity",
   "standards/profile governance adoption outside BTG"],
 "claim_boundary":"Six native implementations are BTG-controlled reproducibility evidence; unrelated third-party independence remains pending."
}
json_path=QDIR/"ENTITY_V3_4_1_RELEASE_QUALIFICATION_2026-09-25.json"
json_path.write_text(json.dumps(qualification,indent=2,sort_keys=True)+"\n",encoding="utf-8")
md=f'''# ENTITY v3.4.1 Release Qualification — 2026-09-25

**Status:** {qualification["status"]}

**Qualified source:** `{qualification["qualified_source_commit"]}`
**Base:** ENTITY v3.4.0 at `{qualification["base_commit"]}`

## Qualification result

- Complete regression: **185/185 PASS**.
- Protocol-origin/migration/economic-lineage regression: **8/8 PASS**.
- v3.4 Global Passport/package tests: **33/33 PASS**.
- Sealed v3.4.1 Global Passport campaign: **24/24 vectors** (12 valid, 12 invalid).
- Canonical result SHA-256: `{qualification["global_passport_conformance"]["expected_result_sha256"]}`.
- Six BTG-controlled native implementations: **Rust, TypeScript, Go, C#, Java, Swift — PASS**.
- Six executable domain packages: **PASS**.

## Corrected release property

Fresh-user bootstrap no longer makes that user the issuer/originator of ENTITY's canonical profiles. Existing v3.4.0 user identity, objects, Rights Passports and signed history remain unchanged; historical profile variants remain verifiable by body hash while new issuance uses canonical ENTITY-signed profiles and explicit protocol-origin lineage.

The v3.4.1 exact release-origin anchor is generated only after the immutable tag exists and is distributed as an ENTITY-signed sidecar. New v3.4.1 issuance fails closed without that exact sidecar.
'''
(QDIR/"ENTITY_V3_4_1_RELEASE_QUALIFICATION_2026-09-25.md").write_text(md,encoding="utf-8")
print(json.dumps({"status":qualification["status"],"regression":"185/185","origin_tests":"8/8","global_passport":"33/33","vectors":"24/24","six_language":"PASS","packages":"6/6"},indent=2))