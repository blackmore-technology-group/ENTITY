# BECP 0.2.0 Qualification Report

Qualification ID: BECP_0.2.0_QUALIFICATION_20260912
Generated UTC: 2026-09-12T21:02:38.579658+00:00
Disposition: QUALIFIED_PASS

## Verified results
- Python compile-all: PASS
- Full pytest regression: PASS — 5/5 tests
- Live TLS/mTLS remote E2E: PASS
- Audit hash-chain verification: PASS
- Current registered certificate fingerprint alignment: PASS
- Physical scope: one physical BTG workstation; ENG-SIM-01 is a separately enrolled logical workstation identity using its own certificate on the same physical BTG host.

## Security scope
Private keys and signing-secret contents are intentionally excluded from this evidence package.
The package records public certificate fingerprints, secret presence, source/config/test hashes, audit-chain evidence, regression results, and live E2E results.
The legacy PKI_MANIFEST.json is recorded as superseded where its BTG fingerprint differs from the currently registered certificate.
