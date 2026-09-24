from __future__ import annotations
import hashlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
KIT = ROOT / "protocol" / "v3" / "ENTITY_V3_2_ADOPTION_CLEANROOM_KIT.min.json"
QUAL = ROOT / "docs" / "qualification" / "ENTITY_V3_2_0_RELEASE_QUALIFICATION_2026-09-24.json"
EXPECTED_KIT = "44e7a00f910c89aced3b3c1b5e9cba486809ca313e9bfb4b7bc9266095c10c14"
EXPECTED_RESULT = "1eb59e09ab08da86bfd8584df4a64ba331f7bbbce3d236b9b94f351606c90e18"
EXPECTED_LIFECYCLE = [
    "DCO", "INSTRUMENT", "LISTING", "DISCLOSURE", "ORDER_RFQ_AUCTION",
    "PRICE_DISCOVERY", "TRADE", "CLEARING", "SETTLEMENT", "ENTITLEMENT",
    "USAGE", "DERIVED_OUTPUT", "ECONOMIC_CONSEQUENCE",
]
errors = []
actual_kit = hashlib.sha256(KIT.read_bytes()).hexdigest()
if actual_kit != EXPECTED_KIT:
    errors.append(f"kit_sha256:{actual_kit}")
kit = json.loads(KIT.read_text(encoding="utf-8"))
qual = json.loads(QUAL.read_text(encoding="utf-8"))
if kit.get("profile", {}).get("expected_result_sha256") != EXPECTED_RESULT:
    errors.append("kit_expected_result")
if len(kit.get("vectors", [])) != 16:
    errors.append("vector_count")
if qual.get("regression") != {"passed": 128, "total": 128, "runner": "tools/run_v3_regression.ps1", "environment": "_venv_entity_v3"}:
    errors.append("regression")
if qual.get("targeted_adoption_tests") != {"passed": 12, "total": 12}:
    errors.append("targeted_adoption_tests")
if qual.get("market_structure_preserved") != EXPECTED_LIFECYCLE:
    errors.append("market_lifecycle")
conf = qual.get("adoption_conformance_vectors", {})
if conf.get("cleanroom_result_sha256") != EXPECTED_RESULT or conf.get("sealed_kit_sha256") != EXPECTED_KIT:
    errors.append("cleanroom_hashes")
cleanrooms = qual.get("cleanrooms", {})
if set(cleanrooms) != {"rust", "typescript", "csharp", "go", "swift", "java"}:
    errors.append("cleanroom_languages")
for language, evidence in cleanrooms.items():
    if evidence.get("status") != "PASS" or not evidence.get("commit") or not evidence.get("workflow_run"):
        errors.append(f"cleanroom:{language}")
result = {
    "valid": not errors,
    "version": qual.get("version"),
    "status": qual.get("status"),
    "kit_sha256": actual_kit,
    "cleanroom_result_sha256": EXPECTED_RESULT,
    "regression": qual.get("regression"),
    "cleanrooms": {k: v.get("status") for k, v in sorted(cleanrooms.items())},
    "errors": errors,
}
print(json.dumps(result, indent=2, sort_keys=True))
sys.exit(0 if not errors else 2)
