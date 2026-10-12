# BTG DataChip Application Architecture — experimental v0.1

Date: 2026-10-12. Non-normative engineering specification. This does not amend ENTITY Protocol 1.0, the protected v3.4.3 tag, or live application binaries.

## The architecture

1. A **native application host** handles OS lifecycle, camera, ARKit, Metal, GPS, display, accessible input, user consent and operating-system permissions.
2. A **DataChip bundle** provides a signed declarative manifest, versioned dependency graph and portable data or safe formula chips.
3. The **ENTITY Data Processor** verifies integrity, resolves dependencies and interprets approved bounded data formulas.
4. **Identity and rights** are authenticated independently: issuer signatures, a separately authenticated host principal, application-specific grants and signed fresh revocation snapshots. Rights metadata never grants itself permission.
5. Shared data may be cached separately by apps for offline operation; sharing a chip does not share private permissions or real-world title.

## App-by-app module targets

| Product | Candidate DataChips | Must remain native or independently qualified |
| --- | --- | --- |
| HuntAR | Spatial, geographic DEM and trails, wildlife, navigation, HUD declarative data, safety, AI inputs, diagnostics | ARKit, Metal, camera, GPS/heading, HUD input, support bridge |
| SearchAR | SAR maps, task plans, search patterns, authorized incident evidence, teams and test definitions | Incident command identity and privacy, device service |
| HikeAR | Trail packs, maps, navigation, safety and incident handoff | Location services, native maps and interface |
| ShowAR | Spatial assets, exhibits, media descriptors | Device rendering and UI |
| GuideProof | Trip templates, evidence schemas, rules and approved offline region packs | Operator authentication, signed documentation |
| ChangeGuard | Comparison policies, document rules, lineage schemas | File access permissions, file parsing and host UI |
| Command Centre | Signed diagnostic definitions, expected results, app manifests and build evidence | Authenticated secure agents, real execution/test evidence |
| FraudStrike | Verified threat indicators, filter configuration and forensic evidence schema | OS-specific telecom filtering and lawful provider actions |
| ENTITY Wallet | Asset formula, Rights Passport references, ticker/listing and transfer envelopes | Signing keys, custody, authorized issuance/trade and real external settlement |
| Other BTG and third-party apps | Data, configuration, bounded reconstruction recipe and semantic views | Native operating-system services and platform approval |

The names above are architectural targets. The current tested pilot uses a synthetic geographic DataChip referenced by signed HuntAR and HikeAR manifests; it has not modified or deployed those apps.

## Current experimental modules

- sdk/datachip/processor.py — offline portable v0.1 exact byte-copy chip.
- sdk/datachip/formula_chip.py — bounded v0.2 atom/entropy/concat/repeat/slice DAG.
- sdk/datachip/rights.py — Ed25519 signed delegation and signed revocation proof, scoped to chip, subject and app.
- sdk/datachip/application.py — signed application bundle and dependency resolver, hash checks, platform and API checks.
- sdk/datachip/host.py — reference signed-bundle plus delegated-rights eligibility plan.

None of those APIs loads native executable code or changes an operating-system entitlement. A signed Rights Passport reference is not a verified legal title. A trusted issuer bridge, revocation governance and externally authenticated user session are required for production.

## Bundle design

The canonical signed manifest defines application identifier, release identifier, expected host ABI, compatible platforms, trusted signer, named DataChip modules, module data categories, content hashes, dependency names and public versus grant-required resource classification.

The host verifies publisher signature against a separately pinned key, verifies each installed chip's independent hash and reconstruction integrity, rejects missing or cyclic dependencies and enforces rights-permitted modules separately. A verified bundle is only a resource plan. Real reads and exports must reverify grant expiry, revocation, audience and authenticated user at use time.

## Future deployment system

A signed native host downloads or installs permitted data packs, verifies hashes and dependency lockfiles, stages the entire new manifest before switching to it, keeps last-known-good offline resources, and supports rollback and revocation with anti-rollback floors. Update/activation/rollback is a future engineering gate, not implemented by the current resolver.

On iPhone, native camera and AR code remain inside the signed app. New app executable functionality must follow App Store requirements, whereas managed data packs can use supported asset delivery systems. A chip is not a loophole for downloading arbitrary executable functionality.

## Command Centre integration

A diagnostic chip will carry versioned declarative test expectations, compatibility IDs and evidence schemas, never privileged arbitrary shell scripts. Native device agents must validate consent, authenticated session, allowed commands and result authenticity. Test definitions cannot impersonate device evidence.

## Qualification gates

1. Formula/entropy exactness, hostile-input fuzzing, memory/CPU/latency limits, full physical footprint benchmarks.
2. Current rights-state attestation from the authoritative ENTITY policy service, key rotation and revocation proof freshness.
3. Cross-platform Rust/Swift/Kotlin/.NET SDK parity and signed native host isolation.
4. Real signed packages, staged atomic activation, rollback, offline cache and compatibility tests.
5. Pilot one consented real trail dataset across HuntAR and HikeAR without changing camera, rendering or core UI functions.
6. Third-party independent reader, independent security review, app-store compliance and lawful global distribution.

No real Boundary Country trail data is bundled in the current synthetic proof-of-concept.
