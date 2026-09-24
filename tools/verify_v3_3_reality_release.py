from __future__ import annotations
import hashlib, importlib.util, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "37_Verifiable_Reality"
KIT_PATH = ROOT / "protocol" / "v3" / "ENTITY_V3_3_REALITY_CLEANROOM_KIT.min.json"
SCHEMA_PATH = ROOT / "protocol" / "v3" / "ENTITY_VERIFIABLE_REALITY.schema.json"
EXPECTED_KIT_SHA256 = "f8b39ee01fb7346f33a57530e925b545d2bf9a770c7ec60724e28a4971d55a46"
EXPECTED_SCHEMA_SHA256 = "6e1c7e621e0aa84627e009febf8999503b7a61f92627b885ed10a19f2ef7d767"
EXPECTED_RESULT_SHA256 = "82bd1f1fb328edd37a26d8ea60ede5a599c7d9af5027bffd73b9e52843b5a51d"

def sha_file(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

errors=[]
if sha_file(KIT_PATH) != EXPECTED_KIT_SHA256:
    errors.append("kit_sha256")
if sha_file(SCHEMA_PATH) != EXPECTED_SCHEMA_SHA256:
    errors.append("schema_sha256")
kit=json.loads(KIT_PATH.read_text(encoding="utf-8"))
if kit.get("version") != "3.3.0" or kit.get("base_release") != "v3.2.0":
    errors.append("kit_version_or_base")
if kit.get("valid_vectors") != 10 or kit.get("invalid_vectors") != 10 or len(kit.get("cases", [])) != 20:
    errors.append("vector_counts")
if kit.get("expected_result_sha256") != EXPECTED_RESULT_SHA256:
    errors.append("kit_expected_result")
if kit.get("schema_sha256") != EXPECTED_SCHEMA_SHA256:
    errors.append("kit_schema_commitment")

spec=importlib.util.spec_from_file_location("reality_profile", SRC/"reality_profile.py")
profile=importlib.util.module_from_spec(spec); sys.modules["reality_profile"]=profile; spec.loader.exec_module(profile)
spec=importlib.util.spec_from_file_location("reality_conformance", SRC/"reality_conformance.py")
conf=importlib.util.module_from_spec(spec); sys.modules["reality_conformance"]=conf; spec.loader.exec_module(conf)
transcript=[]
for case in kit.get("cases", []):
    actual="VALID" if conf.validate_reality_record(case.get("record")) else "INVALID"
    if actual != case.get("expect"):
        errors.append(f"case:{case.get('id')}:{actual}")
    transcript.append({"id":case.get("id"),"actual":actual})
result_hash=hashlib.sha256(canonical(transcript)).hexdigest()
if result_hash != EXPECTED_RESULT_SHA256:
    errors.append(f"result_sha256:{result_hash}")

result={"valid":not errors,"version":"3.3.0","vectors":len(transcript),"valid_vectors":kit.get("valid_vectors"),"invalid_vectors":kit.get("invalid_vectors"),"kit_sha256":sha_file(KIT_PATH),"schema_sha256":sha_file(SCHEMA_PATH),"result_sha256":result_hash,"errors":errors}
print(json.dumps(result,indent=2,sort_keys=True))
sys.exit(0 if not errors else 2)
