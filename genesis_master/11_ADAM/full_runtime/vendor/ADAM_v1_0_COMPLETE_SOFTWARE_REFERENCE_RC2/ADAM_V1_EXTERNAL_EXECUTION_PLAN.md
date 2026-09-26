# ADAM v1.0 External Execution Plan

This package is ready to move into the controlled external qualification program. Execute the gates in this order:

1. **Rust build and conformance:** build the sealed v0.51 Rust workspace on controlled Linux and Windows builders; generate `Cargo.lock`; run unit/property tests, exact R4 vectors, Miri, sanitizers and all fuzz targets; perform independent Rust review.
2. **Hardware custody:** implement the v0.52 provider contract against selected HSM/KMS/PKCS#11 hardware; provision purpose-separated keys; conduct rotation, revocation, backup and recovery ceremonies.
3. **Physical cluster:** install identical signed binaries on at least three independent authority hosts plus independent witnesses; run the complete network/storage/clock/provider fault matrix.
4. **Bounded device pilot:** connect one low-risk device through a certified adapter; complete simulation, digital twin, hardware-in-loop, actuators-disabled and restricted supervised stages.
5. **Real-world training:** register licensed datasets inside ADAM, enforce site/time/device/entity holdouts, train specialist organs and run shadow-only evaluation with drift and rollback.
6. **Freeze production candidate:** bind source, dependency locks, Rust binaries, HSM identities, node identities, deployment topology, device contracts, model versions and SLO thresholds into the v0.56 manifest.
7. **Thirty-day run:** execute the v0.57 controller for thirty actual elapsed days with independent daily witnesses, production workloads and planned fault injections.
8. **Independent assurance:** provide the exact build and all evidence to an external assessor; remediate and retest every critical/high finding; attach the signed assessor receipt through v0.58.
9. **Production promotion:** run `AssuranceCase.promotion_status()`. Production ADAM v1.0 may be signed only when it returns `promotable_to_v1=true` for the exact frozen build.

No local override or configuration flag exists to bypass these gates.
