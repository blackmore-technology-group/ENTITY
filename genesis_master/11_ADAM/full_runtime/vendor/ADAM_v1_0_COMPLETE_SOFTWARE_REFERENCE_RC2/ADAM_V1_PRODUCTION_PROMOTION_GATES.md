# ADAM v1.0 Production Promotion Gates

The candidate must remain blocked until every gate below has evidence bound to the exact source manifest, dependency lock, binaries and deployment digest.

## Gate 1 — Rust authority kernel

Required evidence:

- locked `Cargo.lock`;
- Windows, Linux and additional-architecture debug/release builds;
- exact Python/Rust conformance;
- passing property tests;
- Miri, AddressSanitizer, UndefinedBehaviorSanitizer and ThreadSanitizer evidence;
- completed fuzz campaign with all crashes converted to regression vectors;
- reproducible binary comparison;
- independent Rust review with no unresolved critical/high findings.

## Gate 2 — Hardware custody

Required evidence:

- named HSM/KMS/PKCS#11 provider and validated module identity;
- non-exportable keys;
- purpose-separated hierarchy;
- dual-control/quorum ceremonies;
- rotation, disablement, revocation, backup and disaster-recovery exercises;
- verified absence of production private keys from application memory, logs and archives.

## Gate 3 — Physical distributed authority

Required evidence:

- at least three physically independent authority hosts and independent witnesses;
- no shared authoritative filesystem/database;
- authenticated encrypted transport;
- partition, loss, skew, corruption, disk and provider-outage matrix;
- safety and liveness evidence;
- root convergence and verified recovery.

## Gate 4 — Certified physical pilot

Required evidence:

- bounded device class and certified adapter;
- hardware emergency stop and manual override independent of ADAM;
- hardware-in-loop and restricted-zone evidence;
- command expiry/duplication/identity/fault testing;
- functional-safety professional approval.

## Gate 5 — Licensed real-world training

Required evidence:

- rights, consent, purpose, jurisdiction and retention for every dataset;
- independent train/validation/test isolation by time/site/device/entity lineage;
- calibration, OOD, corruption, adversarial, drift and subgroup analysis;
- shadow deployment evidence;
- independent model promotion and rollback.

## Gate 6 — Thirty actual days

Required evidence:

- frozen candidate and predefined SLOs;
- thirty actual elapsed days;
- daily signed roots and independent witness statements;
- planned fault injections and incident evidence;
- no conflicting authority, invariant violation or hidden reset;
- final reconstruction from genesis.

## Gate 7 — Independent assurance

Required evidence:

- architecture/threat-model review;
- source and dependency review;
- distributed-correctness review;
- custody/cryptography review;
- AI/data-governance review;
- physical-device safety review;
- penetration and supply-chain testing;
- no unresolved critical or high-severity findings;
- signed assessor receipt bound to the exact production build.
