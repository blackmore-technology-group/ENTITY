# ADAM v0.50 External Production Finalization Plan

This plan defines the work that cannot be honestly completed inside the current bounded development environment.

## Program A — Rust authority kernel

**Inputs already supplied**

- Rust source for canonical bonds, hyperbonds, reaction requests and proofs.
- Framed append/replay authority log.
- Canonical conformance vectors.
- Python reference implementation.
- Native C authority reference compiled in the current environment.

**Required external gates**

1. Pin Rust toolchain and dependency lockfile.
2. Compile in clean Linux and Windows builders.
3. Reproduce identical conformance roots across Python, C and Rust.
4. Fuzz canonical decoding, log replay, reaction validation and malformed proof handling.
5. Run Miri, Clippy, sanitizers and dependency audit.
6. Test torn writes, disk-full, power loss, rollback and corrupt-frame recovery.
7. Conduct independent source and binary security review.
8. Produce reproducible signed binaries and software bill of materials.

**Closure evidence**

- Build logs, compiler versions and binary hashes.
- Cross-language vector report.
- Fuzz corpus and crash-free duration.
- Independent audit report and remediation evidence.

## Program B — HSM/KMS key custody

**Required topology**

- Minimum three independent authorities.
- Threshold or majority commit policy.
- Separate witness keys.
- No exportable production private keys.
- Documented ceremony roles and separation of duties.

**Required tests**

- Provisioning ceremony.
- Quorum signing and minority rejection.
- Rotation without history loss.
- Revocation and compromised-node isolation.
- Backup and disaster recovery.
- Jurisdictional key placement.
- Audit-log export and independent verification.

## Program C — Open-world multimodal and temporal training

**Required data program**

- Licensed text, image, audio, video, software, document and sensor datasets.
- Real Operations One temporal histories with consent and governance.
- Field telemetry with synchronized observation and event labels.
- Negative, contradictory, adversarial and OOD examples.

**Required evaluation**

- Semantic grounding accuracy by modality.
- Evidence alignment and citation correctness.
- OOD detection and calibrated abstention.
- Causal intervention tests, not correlation-only scoring.
- Long-horizon temporal prediction.
- Robustness to incomplete, delayed and conflicting evidence.
- Privacy and inference-leakage evaluation.

## Program D — Thirty-day production qualification

The included controller uses monotonic and wall-clock evidence and refuses early or accelerated certification.

**Minimum run**

- 30 actual wall-clock days.
- Representative application, recreation and sensor demand.
- Distributed commits and witness checks.
- Scheduled node loss and recovery.
- Restart and upgrade rehearsal.
- Key rotation rehearsal.
- Latency, throughput, error, recovery-time and resource SLOs.

**Certification rule**

No development simulation or logical-day acceleration may satisfy this gate. Certification requires signed cycle evidence covering the entire elapsed interval with no unresolved invariant, authority, reconstruction or security failure.

## Program E — Independent assurance

Before production use, commission independent reviews of:

- authority and consensus safety;
- cryptography and key management;
- privacy and inference closure;
- embodied-action safety;
- model governance and data rights;
- availability, disaster recovery and operational controls.
