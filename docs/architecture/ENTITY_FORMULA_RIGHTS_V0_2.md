# ENTITY DataChip Formula / Signed Rights v0.2 — Experimental

Date: 2026-10-12. This draft is not the protected ENTITY release or a full live Rights Passport verifier. The new modules are additive and not wired into production Wallet, HuntAR or other BTG apps.

## Formula-native EDC

File suffix .edcf (the existing .edc v0.1 byte-copy format is unchanged).
The artifact is an uncompressed ZIP of canonical JSON and a closed set of
digest-addressed entropy segments. Supported formula instructions are:
ATOM (one byte), ENTROPY (exact retained bytes), CONCAT (ordered children),
REPEAT (bounded repeated basis) and SLICE (bounded range of child).

The format uses topologically ordered node indices, deterministic canonical
manifests, content SHA-256, deduplicated entropy files and a formula chip hash.
No formula instruction invokes Python, device APIs or a remote service.
The verifier checks all output bytes and blocks unknown operations.
Limits: 64 MiB output, 8192 nodes, DAG depth 64, 1 MiB entropy leaf,
2 MiB manifest, physical archive size cap and bounded expansion.
These limits are initial engineering restrictions, not a security certification.

A real BTDU formula can be traversed and converted to portable nodes;
BTDU semantic-tape leaves without a portable dictionary are reconstructed
into retained entropy leaves. This preserves exactness, not maximal compression.
A complex file cannot be reconstructed without preserving irreducible information.

## Signed delegation for offline apps

Experimental Ed25519 grant fields bind a chip ID to a specific subject,
application audience, permitted action (data export), Rights Passport
reference, start/end time and a unique grant ID. Signed revocation snapshots
must be fresh (at most 24 hours), explicitly cover the rights issuer, and
must be verified against separately pinned trusted revocation public keys.

The consumer must obtain a trusted authenticated subject and app identity
from the native host, not from user-supplied metadata or the chip itself.
It must reject grants that are expired, for another app/user/chip, revoked,
or lack fresh status coverage. All positive fixtures use temporary synthetic
test keys only. Private signing keys are never written into the repository.

This verifies a signed *delegated claim*, not necessarily legal title,
independent truth, or the source ENTITY Rights Passport's current status.
A production rights attestation authority must inspect the authoritative
ENTITY policy state and issue revocable grants with verifiable scope. The
native host must revalidate at actual data access time.

## Signed application bundle

The app module manifest is separately signed by a pinned release authority
and contains datachip content hash, module type, dependency graph, compatible
host ABI, application ID and platform. It cannot execute native code, acquire
new OS privileges, update apps or confer data rights by itself.

A bundle may be reused by multiple apps only when each app verifies its own
signed app-specific resource plan and independent per-user entitlement.
Reference host integration returns an eligibility plan, not a persistent
authenticated mount or native device permission.

## Known gaps

- No signed cryptographic chain from the live ENTITY Rights Passport registry
  to delegated grant issuance in this prototype.
- Revocation snapshots need a production availability and issuance policy,
  operational key custody, rollback prevention and hardware-backed signers.
- No fully portable semantic dictionary or formula optimizer parity for every
  BTDU opcode/semantic grammar variant.
- No Rust/Swift/Kotlin native verifier, actual signed app-host loader,
  transactional pack activation or rollback manager.
- No field-ready geographic pack, mobile app build or external audit.
- No compression, cost, throughput, power, GPU or memory superiority proven
  by a synthetic repetitive trial.

## Regression and demonstration

On Windows in the isolated engineering workspace:

    python -B -m unittest discover -s tests -p "test_entity_datachip*.py" -v
    python -B -m unittest discover -s tests -p "test_btg*.py" -v
    python -B examples/btg_shared_geography_demo.py

CI matrix for the new modules is Windows, Linux and macOS in the existing
DataChip portability workflow. Before promotion, check repository-wide CI,
CodeQL, misuse-resistance tests, external signature interoperability and
real offline native use with honest source/total-storage accounting.
