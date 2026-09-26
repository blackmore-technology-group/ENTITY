from __future__ import annotations
from pathlib import Path
import hashlib, json, subprocess, sys, time

ROOT = Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
TEST = ROOT / "16_Test_Qualification" / "unit" / "test_canonical_economics.py"
IMPL = ROOT / "01_Core_Runtime" / "service_runtime" / "canonical_economics.py"
EXTERNAL_AUTH = ROOT / "21_Corporate_Capital" / "external_authorities" / "canonical_external_authority.py"
EVIDENCE = ROOT / "16_Test_Qualification" / "evidence" / "ENTITY_ECONOMIC_QUALIFICATION_CURRENT.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    run = subprocess.run([sys.executable, "-m", "pytest", str(TEST), "-q"], cwd=str(ROOT), capture_output=True, text=True)
    payload = {
        "schema": "entity-economic-qualification-v1",
        "generated_at_ms": int(time.time()*1000),
        "status": "PASS" if run.returncode == 0 else "FAIL",
        "qualification_complete": run.returncode == 0,
        "pytest_exit_code": run.returncode,
        "pytest_output": (run.stdout + "\n" + run.stderr).strip(),
        "implementation_sha256": sha(IMPL),
        "external_authority_verifier_sha256": sha(EXTERNAL_AUTH),
        "test_sha256": sha(TEST),
        "requirements_sha256": sha(ROOT / "01_Core_Runtime" / "ENTITY_REQUIREMENTS.md"),
        "invariants": [
            "explicit payer/payee direction",
            "unique immutable transaction nonce",
            "duplicate/replay settlement rejection",
            "external payment requires provider-confirmed evidence",
            "strong external-payment mode cryptographically verifies the payment-provider attestation and rejects tampering",
            "finalized double-entry postings balance",
            "reversal/refund uses compensating entries",
            "potential value is never represented as cash",
            "REALIZED requires verified external settlement evidence",
            "royalty allocation is deterministic/versioned/conservative",
        ],
        "limitations": [],
    }
    sealed = json.dumps(payload, sort_keys=True, separators=(",",":"), default=str).encode()
    payload["evidence_sha256"] = hashlib.sha256(sealed).hexdigest()
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status":payload["status"],"evidence":str(EVIDENCE),"evidence_sha256":payload["evidence_sha256"]}, indent=2))
    return run.returncode


if __name__ == "__main__":
    raise SystemExit(main())
