from __future__ import annotations
import hashlib, json, pathlib, sys

REPO = pathlib.Path(__file__).resolve().parents[1]
DATE = "2026-09-23"
BASE_FILES = [
    "docs/qualification/ENTITY_V3_0_0_RELEASE_QUALIFICATION_2026-09-23.json",
    "docs/qualification/ENTITY_V3_BTG_POLYGLOT_QUALIFICATION_2026-09-23.json",
    "docs/qualification/ENTITY_V3_INTERNAL_SCALE_QUALIFICATION_2026-09-23.json",
    "docs/qualification/ENTITY_V3_INTERNAL_MARKET_SCALE_QUALIFICATION_2026-09-23.json",
    "docs/qualification/ENTITY_V3_INTERNAL_OPERATIONAL_SOAK_2026-09-23.json",
    "docs/qualification/ENTITY_V3_INTERNAL_CRYPTO_ASSURANCE_2026-09-23.json",
    "docs/qualification/ENTITY_V3_INTERNAL_PRIVACY_CRYPTO_ASSURANCE_2026-09-23.json",
    "docs/compliance/ENTITY_V3_REGULATORY_ENGINEERING_MATRIX_2026-09-23.md",
    "docs/compliance/ENTITY_V3_REGULATORY_ENGINEERING_MATRIX_2026-09-23.json",
    "qualification/v3-btg-internal/README.md",
    "tools/qualify_v3_internal_scale.py",
    "tools/qualify_v3_internal_market_scale.py",
    "tools/qualify_v3_internal_soak.py",
    "tools/qualify_v3_internal_crypto.py",
    "tools/qualify_v3_internal_privacy_crypto.py",
    "tools/verify_v3_btg_polyglot.py",
    "tools/seal_v3_btg_internal_closeout.py",
    "tools/verify_v3_btg_closeout_manifest.py",
]
KIT = sorted((REPO / "qualification/v3-btg-internal/CONFORMANCE_KIT").glob("*"))
RESULTS = sorted((REPO / "qualification/v3-btg-internal/results").rglob("*"))
FILES = BASE_FILES + [p.relative_to(REPO).as_posix() for p in KIT if p.is_file()] + [p.relative_to(REPO).as_posix() for p in RESULTS if p.is_file()]

def load(rel: str):
    return json.loads((REPO / rel).read_text(encoding="utf-8-sig"))

def sha(rel: str) -> str:
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()

missing = [p for p in FILES if not (REPO / p).is_file()]
if missing:
    raise SystemExit("missing evidence: " + ", ".join(missing))
release, poly, scale, market, soak, crypto, privacy, reg = (
    load(BASE_FILES[0]), load(BASE_FILES[1]), load(BASE_FILES[2]), load(BASE_FILES[3]),
    load(BASE_FILES[4]), load(BASE_FILES[5]), load(BASE_FILES[6]), load(BASE_FILES[8])
)
checks = {
    "release_gate": release.get("status") == "BTG_INTERNAL_QUALIFIED_FOR_OPEN_SOURCE_RELEASE" and release.get("evidence", {}).get("complete_regression") == {"passed": 90, "total": 90},
    "polyglot": poly.get("status") == "PASS" and len(poly.get("implementations", {})) == 5 and poly.get("cross_language_state_agreement") and poly.get("cross_language_recovery_agreement") and poly.get("cross_language_result_agreement"),
    "persistence_scale": scale.get("pass") is True and scale.get("assets") == 1_000_000 and scale.get("events") == 3_000_000 and scale.get("sqlite_quick_check") == "ok",
    "market_scale": market.get("pass") is True and market.get("total_fully_settled_trades", 0) >= 4_000,
    "operational_soak": soak.get("pass") is True and soak.get("target_total_wall_seconds", 0) >= 900,
    "crypto_assurance": crypto.get("pass") is True and crypto.get("total_adversarial_cases", 0) >= 5_400,
    "privacy_crypto_assurance": privacy.get("pass") is True and privacy.get("total_assertions", 0) >= 3_000,
    "regulatory_engineering": reg.get("status") == "INTERNAL_ENGINEERING_MAPPING_COMPLETE",
}
status = "PASS" if all(checks.values()) else "FAIL"
record = {
    "schema": "entity-v3-btg-internal-closeout-v1",
    "date": DATE,
    "status": status,
    "classification": "BTG_INTERNAL_POST_RELEASE_QUALIFICATION_CLOSEOUT",
    "release": {"tag": "v3.0.0", "commit": "63acd0962965eda1f80bc8afc6259029daaec7aa", "snapshot_sha256": "b08d691922928a4e2c1fecb2d18bb3c22f5856480f140337a946ebb047ab114a"},
    "checks": checks,
    "metrics": {
        "languages": len(poly.get("implementations", {})),
        "invalid_vectors_rejected_each": poly.get("sealed_kit", {}).get("invalid_vectors"),
        "assets": scale.get("assets"), "events": scale.get("events"),
        "market_scale_trades": market.get("total_fully_settled_trades"),
        "soak_seconds": soak.get("target_total_wall_seconds"), "soak_trades": soak.get("total_settled_trades"),
        "signature_replay_crypto_cases": crypto.get("total_adversarial_cases"),
        "privacy_crypto_assertions": privacy.get("total_assertions"),
    },
    "release_boundary_status": {
        "cross_language_live_v3_interoperability_pending": "CLOSED_FOR_BTG_CONTROLLED_TRANSACTION_RECOVERY_INTEROP; EXTERNAL_UNRELATED_INTEROP_REMAINS",
        "production_exchange_capacity_not_certified": "CLOSED_FOR_BTG_INTERNAL_TECHNICAL_SCALE_AND_CONTINUITY; EXTERNAL_SLA_OR_INDEPENDENT_CERTIFICATION_NOT_CLAIMED",
        "external_unrelated_party_v3_reimplementation_pending": "EXTERNAL_PENDING",
        "independent_external_crypto_review": "EXTERNAL_PENDING; BTG_INTERNAL_ASSURANCE_CLOSED",
        "regulatory_classification_not_determined_by_protocol": "ENGINEERING_MAPPING_CLOSED; DEPLOYMENT_SPECIFIC_EXTERNAL_CLASSIFICATION_REMAINS",
        "legal_title_not_determined_by_protocol": "PERMANENT_PROTOCOL_TRUTH_BOUNDARY",
        "market_value_not_declared_by_protocol": "PERMANENT_PROTOCOL_TRUTH_BOUNDARY",
        "external_payment_evidence_is_attestation_not_absolute_truth": "PERMANENT_PROTOCOL_TRUTH_BOUNDARY",
    },
    "internally_closed": [
        "five-language BTG-controlled v3 transaction/recovery conformance and deterministic cross-language agreement",
        "million-asset / multi-million-event persistent-state qualification",
        "sustained real EEP execution scale qualification",
        "bounded operational continuity soak with periodic implementation reopen",
        "signature/replay/canonical-wire/payment-attestation misuse assurance",
        "selective-disclosure and AES-GCM privacy-primitive assurance",
        "regulatory engineering/control mapping",
        "v3.0.0 destructive recovery, concurrency, atomic rollback and execution-time economic binding",
    ],
    "external_remaining": [
        "unrelated third-party v3 implementation and external live interoperability",
        "independent external security/cryptographic review",
        "deployment-specific external legal/regulatory classification or validation where required",
    ],
}
json_path = REPO / "docs/qualification/ENTITY_V3_BTG_INTERNAL_CLOSEOUT_2026-09-23.json"
json_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
md_path = REPO / "docs/qualification/ENTITY_V3_BTG_INTERNAL_CLOSEOUT_2026-09-23.md"
md_path.write_text(f"""# ENTITY v3 — BTG Internal Post-Release Qualification Closeout

Date: {DATE}  
Release: `v3.0.0`  
Release commit: `63acd0962965eda1f80bc8afc6259029daaec7aa`  
Status: **{status}**

This addendum does not modify the immutable v3.0.0 release tag. It records qualification work completed by Blackmore Technology Group after release.

## BTG-controlled tracks closed

- Five native implementations — Rust, TypeScript, C#, Go and Swift — independently accepted the same valid v3 transaction/recovery inputs, rejected all eight invalid vectors, and converged on identical state, recovery and result hashes.
- Persistent-state scale: **{scale.get('assets'):,} assets and {scale.get('events'):,} events**, close/reopen verified, SQLite quick-check `ok`.
- Sustained market execution: **{market.get('total_fully_settled_trades'):,} fully settled EEP trades** across reference and qualification-mirror implementations.
- Operational continuity soak: **{soak.get('target_total_wall_seconds')} seconds**, periodic implementation reopen, **{soak.get('total_settled_trades'):,} settled trades**.
- Cryptographic misuse assurance: **{crypto.get('total_adversarial_cases'):,}** signature/replay/canonicalization/payment-attestation attack cases passed.
- Privacy assurance: **{privacy.get('total_assertions'):,}** selective-disclosure and AES-GCM assertions passed.
- Regulatory engineering/control mapping completed for the documented Canadian, British Columbia, European Union and United States baselines.
- The v3.0.0 release's destructive recovery, concurrency, rollback and execution-time economic-binding evidence remains part of the qualification chain.

## What remains external

1. **Unrelated third-party v3 implementation and external live interoperability.** BTG-controlled cross-language transaction/recovery interoperability is closed; independence cannot be self-certified.
2. **Independent external security/cryptographic review.** BTG internal assurance is closed; an independent review requires an outside reviewer.
3. **Deployment-specific external legal/regulatory classification or validation where required.** Engineering mapping is closed; legal/regulatory determinations for a real venue or instrument remain external.

## Permanent truth boundaries

Legal title, objective external-bank truth, market value and accounting fair value are not created by ENTITY protocol records. BTG internal performance qualification is not an external SLA or independent production certification.
""", encoding="utf-8")
all_files = FILES + [json_path.relative_to(REPO).as_posix(), md_path.relative_to(REPO).as_posix()]
entries = [{"path": p, "sha256": sha(p)} for p in sorted(set(all_files))]
material = "\n".join(f"{x['path']}|{x['sha256']}" for x in entries).encode()
manifest = {"schema": "entity-v3-btg-internal-closeout-manifest-v1", "date": DATE, "status": status, "files": entries, "snapshot_sha256": hashlib.sha256(material).hexdigest()}
(REPO / "ENTITY_V3_BTG_INTERNAL_CLOSEOUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"status": status, "snapshot_sha256": manifest["snapshot_sha256"], "files": len(entries)}, indent=2))
sys.exit(0 if status == "PASS" else 2)
