# Migration from ADAM v0.50 to v0.50.1

v0.50.1 preserves the v0.50 architecture and API surface while hardening unsafe development mechanisms and correcting integrity/security defects.

Important compatibility changes:

- Cognition model files now use validated JSON. Legacy pickle files are rejected and must be retrained/exported.
- v0.44 bond termination is represented through immutable successor bonds plus a supersession map.
- Quorum certificates now include explicit membership and quorum fields.
- Modified quorum/key-custody receipt bodies are rejected.
- Encrypted atom identities include governed metadata, policy and jurisdiction; atom IDs may therefore differ from v0.50.
- The native C log format changed to canonical big-endian restart-verifiable frames. Old development logs require one-time migration or recreation.
- Rust source key files use `<log path>.ed25519`; external production builds should replace file custody with HSM/KMS custody.

The original v0.50 tree remains preserved separately for reproducibility.

Additional v0.50.1 operational changes:

- Isolated signer and authority workers now close inherited pipe endpoints and complete bounded join/terminate/kill cleanup.
- Qualification runs each test file in an isolated interpreter and emits hash-stamped per-file evidence.
- Runtime and optional qualification dependencies are audited separately.
- The mechanical audit now scans Rust, C, shell, PowerShell and project metadata in addition to operational Python.
