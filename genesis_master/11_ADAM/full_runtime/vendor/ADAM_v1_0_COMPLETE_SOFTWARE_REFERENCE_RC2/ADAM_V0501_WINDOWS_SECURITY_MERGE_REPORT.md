# ADAM v0.50.1 Windows and Source-Audit Merge Report

**Release:** `0.50.1.dev4`  
**Classification:** Source-audited, production-hardened, cross-platform reference build  
**Production certified:** No

## Merge decision

The v0.50.1 source-audited branch is the authority for security, serialization, content-address integrity, physics immutability, certificate verification and source qualification. The Windows-hardened branch contributes the cross-platform atomic authority writer, optional AES-GCM encrypted Ed25519 key storage, Windows-safe process-spawn paths and a byte-compatible native framing fallback.

Both distributed ZIPs are generated from this single source tree. There is no weaker Windows-only security branch.

## Security and integrity remediations retained

- Deterministic schema-validated cognition serialization; legacy pickle rejected.
- Restricted AST expression evaluator; runtime `eval` and `exec` absent.
- Immutable bond termination through successor/supersession state.
- Minimum and maximum valence enforcement.
- Proposer, approver and capability context bound into reaction identities.
- Frozen law and reaction registries after authoritative operation begins.
- Explicit membership and quorum bound into certificates.
- Direct witness statement, identity, root, chain and signature verification.
- Cryptographically complete signing receipts.
- Security metadata included in atom identity and AEAD authentication.
- Restart-safe native framing reference with stale-root and tamper rejection.
- Persistent signing identity in both Rust source targets.
- Raw secret-file release gate.
- Bounded isolated-process cleanup.
- Per-file interpreter isolation with leak/result checks.
- Runtime and qualification dependency separation.

## Windows hardening retained

- No direct dependency on POSIX-only `os.fchmod`.
- Temporary descriptors close before cleanup and replacement.
- Atomic file replacement and best-effort platform permissions.
- Forced `spawn` qualification path for isolated authority processes.
- Parent-side materialization of deterministic physics state for spawn compatibility.
- Python framing reference on Windows when a POSIX C/OpenSSL toolchain is unavailable.
- The Python and C references use the same canonical frame format, hash domain, replay rules and stale-root semantics.

## Qualification boundary

The build provides executable source-audited reference logic. External certification still requires real HSM/KMS custody, compiled/fuzzed/independently reviewed Rust kernels, physical devices, multi-host WAN and jurisdiction testing, actual wall-clock soak, and independent security and safety review.
