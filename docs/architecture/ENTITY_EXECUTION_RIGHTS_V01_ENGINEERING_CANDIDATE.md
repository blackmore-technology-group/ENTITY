# ENTITY DataChip Execution Rights Profile v0.1 — Experimental

**Status:** ENGINEERING CANDIDATE. This is a distinct optional execution-rights profile. It is not an amendment to frozen ENTITY Protocol 1.0, does not repurpose existing `entity-edc-signed-rights-grant-v0.2`, and does not promote any deployed host to production.

## Why separate EXECUTE from EXPORT

Current `sdk/datachip/rights.py` authorizes **only** `dataplane:export` with an explicit trusted delegation and signed revocation. A wallet position or a data export license does not authorize running a DataChip. These scopes must never be inferred from each other.

New experimental interfaces:
- `sdk/datachip/execution_rights.py`: Reads a real ENTITY `RightsPassportRegistry` and verifies the authoritative **signed** Rights Passport against the live read-only SQLite status. Checks a single active, unsuperseded controller/object version with an unconditional EXECUTE or DATAPLANE:EXECUTE ALLOW and no conflicting prohibition or conditional rule.
- Grant issuance requires an **authenticated** controller decision, a separately supplied issuer signer (approved production HSM/KMS required later), and independent verification against pre-pinned Ed25519 issuer public keys. At most 900-second lifetime. The module contains no private keys and offers no self-service public issuance endpoint.
- Consumer verifies versioned Ed25519 signatures and domain separation for both execution grant and complete signed revocation snapshot. It rejects stale snapshots, revoked grant/issuer/passport, insufficient issuer coverage, mismatched chip/content/assembly/subject/app/device and rollback below an externally protected monotonic checkpoint.
- The authenticated license/entitlement service and the verified device-identity service are **separate mandatory callbacks**. Each must return exactly True. Neither comes from the chip, wallet UI, or a client-supplied string.
- `sdk/datachip/execution_host.py`: Executes the single allowlisted bounded ASCII-uppercase transform *after* genuine EDCF v0.2 verification, signed rights/revocation, independent license and device checks. Uses the ENTITY bounded formula evaluator in memory and returns only a computed output digest. No arbitrary code or raw file export.

## Current tests

On **BTG Windows 11**, an isolated checkout of the genuine current ENTITY SDK and RightsPassportRegistry implementation passed **28/28 tests** (October 13, 2026). The test fixture creates a temporary SQLite registry with synthetic controller identities, ephemeral Ed25519 issuer and revocation keys, and a real EDCF-v0.2 formula made with `pack_formula_bytes`. Tests reject supersession, ambiguous active passports, conditional rights, PROHIBIT, EXPORT-only, untrusted/absent signers, revocation, signer key mismatch, stale checkpoint, denied independent license/device, tampering, and unsupported computation.

The original separate Stage 7 lab package also has 49/49 local tests, but those are a different implementation and scope; do not sum them as one suite.

## Still BLOCKING production

- Approved corporate/entity controller identity backed by a real ENTITY signing manifest, and authenticated controller authorization (not the synthetic fixture).
- Real, provisioned private signing keys managed by a production HSM/KMS, published and pinned issuer and revocation trust roots, delegated issuer policy and key lifecycle.
- **Authoritative live revocation ledger** delivering complete signed fresh status, append-only publication/availability, secure timestamps and protected per-host sequence antirollback.
- Production license entitlement service and properly enrolled/attested device identities. Present test adapters are stub approvals/denials, **not** authoritative economic or device systems.
- Transactional consistency between authoritative Rights Passport state, issuance, and revocation publication. The current reference read-rechecks status but cannot prevent a concurrent post-issuance supersession without a live revocation service.
- Independent review and fuzzing of EDCF parser, sandbox/runtime boundaries, whole-repository CI runner pass, secure device host, independent Swift/Kotlin/Rust compatibility, app integration, and economic settlement evidence.

**Required result flags for this candidate:** `production_issuer_connected=false`, `hardware_identity_attested=false`, `production_ready=false`. Never claim these tests connected production credentials or legal rights.
