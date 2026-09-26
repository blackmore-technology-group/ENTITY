# ADAM v0.51 Engineering Contract

## Release identity

- Branch: `adam-v0.51-rust-authority-source-qualification-candidate`
- Version: `0.51.0.dev1`
- Parent oracle: ADAM v0.50.1 R4, version `0.50.1.dev4`
- Promotion target: **ADAM v0.51 — Compiled Authority and Information-Physics Kernel**

## Non-negotiable authority rules

1. R4 remains immutable and is never silently rewritten to make Rust agree.
2. Canonical bytes define content identities; equivalent logical values must encode identically.
3. Every authoritative transition begins from an expected universe root.
4. Simulation cannot mutate authoritative state.
5. Invalid reactions cannot change the root.
6. Bonds are immutable; termination creates a successor and supersession relation.
7. Constitutional laws, valence, authority and capability requirements run before commit.
8. A commit emits a proof, updated worldlines and a new deterministic root.
9. Durable journal append and synchronization occur before active in-memory promotion.
10. Recovery re-executes history and rejects proof, signature, sequence or root divergence.
11. Checkpoints accelerate recovery but are never trusted as an alternative authority history.
12. Rust cannot be promoted from shadow mode until exact conformance and all external gates pass.

## Canonical conformance contract

Rust must reproduce the frozen R4 oracle for:

- primitive MessagePack boundaries;
- atom, bond and hyperbond identities;
- reaction-definition and reaction-instance identities;
- canonical bytes;
- proof identities;
- universe and algebra roots;
- immutable supersession;
- entity worldlines;
- checkpoint state;
- reconstruction output.

The sealed oracle contains 24 primitive vectors and 20 state transitions. One mismatch blocks promotion.

## Persistence contract

The Rust authority source defines:

- checksummed framed journal records;
- explicit sequence and previous-root binding;
- enrolled authority-key binding;
- signature verification during replay;
- torn-tail truncation only at the final incomplete frame;
- rejection of complete-frame tampering and reordered history;
- immutable root-addressed checkpoints;
- checkpoint signature, key and state-root verification;
- full replay from genesis with checkpoint comparison;
- stale-root rejection and deterministic restart.

## Development signer boundary

The included file-backed Ed25519 signer exists only to qualify authority semantics and replay. Production custody is a v0.52 gate and requires non-exportable HSM/KMS keys, provider attestation, rotation ceremonies and disaster-recovery qualification.

## Promotion gate

The candidate may be promoted only after:

- Cargo and rustc compile every target on the declared platforms;
- a sealed `Cargo.lock` exists;
- Clippy accepts no warnings;
- Rust tests and property tests pass;
- exact R4 conformance passes;
- replay and recovery fault tests pass;
- Miri and required sanitizers pass;
- all fuzz targets complete the accepted campaign with no unresolved finding;
- clean builders reproduce accepted binaries or accepted code/data-section hashes;
- signed manifests and SBOMs are generated from resolved dependencies;
- an independent Rust security review has no unresolved critical or high finding.

Until then, the classification remains **source qualification candidate**.
