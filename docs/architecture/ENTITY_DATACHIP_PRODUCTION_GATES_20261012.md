# ENTITY / BTG DataChip production qualification gates

Date: 2026-10-12. Status: **in engineering, NOT authorized for live mobile production**.

## Scope and live-state boundary

The protected ENTITY v3.4.3 tag stays immutable. Formula-native chips and signed application bundles are additive post-tag implementation on main. Production ENTITY wallet databases, the Rights Passport registry, HuntAR 475, SearchAR, HikeAR, GuideProof and Command Centre runtime remain unchanged unless each release owner explicitly approves a separately qualified deployment.

The technology is a *signed, offline application data delivery stack*. DataChip packages contain data and deterministic bounded formulas, **not** unrestricted executable code. The native iOS/Android/Windows/Linux host controls permissions, actual hardware, secure sessions, App Store release and diagnostics.

## Validated in current reference code

1. Formula-native EDC: deterministic DAG with bounded ATOM, ENTROPY, CONCAT, REPEAT and SLICE; stored irreducible data is required; exact-hash verification and negative parser tests.
2. Signed, app-scoped Ed25519 delegation with issuer keys pinned out of band, validity window and freshness-controlled signed revocation snapshot.
3. Signed application bundle and module dependency resolution; the same synthetic trail chip can be referenced by HuntAR and HikeAR with different audience-bound grants.
4. **Issuer-side, read-only authoritative Rights Passport bridge**: calls the existing RightsPassportRegistry.get/verify, separately reads live SQLite status, rejects superseded/ambiguous passports, rejects missing/unconditional/PROHIBIT/conditional/obligated export rules, and requires an independent controller-authenticated approval callback before a short-lived delegated grant. It never stores a signing key or modifies a production registry.
5. **Data-only deployment manager**: copies locally approved signed packages to a staging directory, independently re-verifies the bytes and signed manifest, atomically switches the active release pointer, retains last known good, revalidates on cold restart, rejects accidental downgrade, serializes cross-process installation, and detects staged failures.

All above are **reference implementation**, not a certified security boundary or installed app-host release. Local synthetic tests cannot substitute for device/production tests.

## Critical production blockers

| Gate | Requirement | Current evidence/status |
| --- | --- | --- |
| AUTH-01 | Real independently authenticated user/controller sessions and reliable controller-to-issuer KMS/HSM authorization; sign only after current authoritative ENTlTY passport rule evaluation | **BLOCKED**. Reference bridge checks registry and requires callback; production identity/authenticated issuance service and external KMS not qualified |
| AUTH-02 | Offline clients receive complete, signed, fresh revocation/status proofs with coverage, independent trusted key roots, key rollover, revocation edge cases and clock rollback defense | **BLOCKED**. Signed test snapshots and stale-status denial work; operational distribution and secure time not qualified |
| DIST-01 | Signed host ABI on actual iOS/Android/Windows/Linux; Rust library and secure Swift/Kotlin/.NET bindings with same positive/negative vectors | **BLOCKED** until native SDK/device tests |
| DIST-02 | Trusted monotonic anti-rollback counter in OS-secure storage; atomic staging/activation under abrupt power loss, disk full, interrupted copy, concurrent processes, damaged pointer and key compromise | **PARTIAL** reference atomic switch; local pointer/floor can be rolled back by an attacker with full filesystem control |
| DIST-03 | Offline region packs verified using licensed real-world data; coordinates, unit scale, map colors, PII and safety rules tested on device | **BLOCKED**. Only synthetic geographic fixtures |
| APP-01 | HuntAR native host shadow-mode reader, real iPhone ARKit/Metal/camera/GPS/UI compatibility, support bridge, offline baseline equal to old loader | **BLOCKED**. No change to HuntAR 475 approved or performed |
| APP-02 | SearchAR/HikeAR/GuideProof/FraudStrike/ChangeGuard standalone opt-in and permission boundary tests | **BLOCKED**. Architecture only |
| SEC-01 | Adversarial third-party fuzzing, dependency/SBOM/SLSA, code signing, independent security review, provenance and malicious package tests | **BLOCKED**. GitHub CI and local tests do not qualify hostile field inputs |
| OPS-01 | Product security and privacy policy, updates/rollback runbooks, service monitoring, incident response, support restrictions, disaster recovery, signed release attestations | **BLOCKED**. No live deployment yet |
| PERF-01 | Independent benchmarks for exactness/total physical footprint, CPU/latency/RAM/battery on real content compared with optimized baseline | **BLOCKED**. Synthetic repetition does not prove real compression savings |

## Safety requirements

- Any live grant must be issued by a separately authenticated, currently authorized controller. Validating a passport signature alone is insufficient; current authoritative state MUST be checked.
- The exact current Rights Passport is scoped to the ENTITY object, and a PROHIBIT/conditional rule can never be silently ignored. Ambiguous simultaneous active versions MUST fail closed.
- A delegated signed grant MUST specify chip ID, app audience, user identity, action, rights-reference and expiry. Clients MUST trust pinned signing and status keys from a separate enrollment process, never public keys provided by the chip itself.
- Production issuer signing keys MUST be held by KMS/HSM/secure hardware, not app assets or repository secrets.
- A verified bundle is only a data plan, not a permission. All reads/exports must recheck active rights and revocation at the time of use.
- A signed app bundle may update only supported *data assets*; native code, AR rendering, telephony screening or device support agents remain native and platform-reviewed.
- Local anti-rollback is not a secure monotonic counter. Do not claim a compromised-device replay attack is prevented by an ordinary filesystem pointer.
- Existing original BTDU source and complete entropy must not be deleted solely because a new DataChip package reconstructs successfully once.
- High-consequence geographic/safety data must fail safe if an authoritative rule or data pack is stale or unavailable, with user-visible limitations rather than fabricated accuracy.

## Safe forward-only recovery

Keep old verified packages for forensic and operational recovery, but do NOT silently activate a lower signed sequence. A qualified controller must sign a **new higher-sequence bundle** pointing to the previously qualified data pack; only that forward release may be activated after all current rights, revoked-content and compatibility checks. The prototype validates the sequence and hashes but does not yet manage real issuer/incident approvals.

## Acceptance program

1. Freeze golden vectors and specification; independent Rust reader implements them.
2. Qualify authoritative read-only policy query with real configured runtime identity, current live statuses and authorized test passport, using synthetic data and without editing production.
3. Put issuance into independent KMS/HSM-backed authenticated authority endpoint with signed revocation publication.
4. Qualify native SDK under Swift/iOS, Kotlin/Android and Windows on hardware, plus offline failure and restart.
5. Demonstrate data-only signed versions from current to next, interrupted staging, forward-only recovery and revocation on two independently controlled devices.
6. Pilot one licensed BC trail network in HuntAR shadow mode with measured data parity and no changes to camera, AR, HUD, native map or support bridge.
7. Independent security assessor signs findings, BTG release board accepts risk, documented rollback and recovery plan, then opt-in limited deployment.
8. Only after all gates are evidenced may production status be asserted.

## Scope of current actions

The model has authorization to develop, test and push an additive source module; it **does not** imply approval to issue real trade rights, modify owner identity, delete any data, replace the ENTITY wallet runtime, bypass app-store code distribution rules, or submit a HuntAR build.

See corresponding tests for exact repeatable evidence; passing synthetic tests are not claims of global adoption.
