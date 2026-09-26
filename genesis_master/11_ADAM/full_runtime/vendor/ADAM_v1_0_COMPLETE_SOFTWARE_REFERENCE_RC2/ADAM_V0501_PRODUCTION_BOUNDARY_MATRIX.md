# ADAM v0.50.1 Production Boundary Matrix

| Area | Status in v0.50.1 | Local evidence | External completion still required |
|---|---|---|---|
| Atomic/bond/reaction kernel | Operational bounded Python reference | 47/47 v0.44-v0.50 tests; 9/9 integrated gates | Rust compile, fuzz, Miri and independent review |
| Content-address integrity | Immutable supersession implemented | Repeated reaction and digest-consistency tests | Production storage stress and fault injection |
| Symbolic proof expressions | Restricted AST evaluator operational | Malicious-expression adversarial tests | Larger theorem domains and formal verification |
| Cognition persistence | Validated JSON decision-table format | Round-trip and malicious-pickle rejection | Safe large-model tensor/container standard |
| Quorum certificates | Explicit membership/quorum bound | Duplicate, forged and threshold tests | Real transport and BFT/WAN qualification |
| Witnessing | Supplied statements directly verified | Forged and duplicate witness tests | Independent witness operators |
| Key custody | Isolated software quorum reference with clean shutdown | Receipt-binding and worker-leak tests | HSM/KMS/PKCS#11 hardware ceremonies |
| Encryption/erasure | Metadata and policy-bound AEAD reference | Tamper and erasure tests | Hardware roots and legal retention program |
| Native C target | Compiled framing/hash-chain reference | Restart, stale-root and tamper tests | Not a signing authority |
| Rust v0.43 target | Source-hardened, uncompiled | Static gates; no stub macros | External cargo/rustc build and audit |
| Rust v0.44 target | Source-hardened, uncompiled current target | Static gates; no stub macros | External cargo/rustc build and audit |
| Application adapters | Explicit abstract contracts plus references | v0.46 tests | Product-specific connectors |
| IoT/robotics | Governed capability/command reference | v0.48 tests | Real hardware and safety certification |
| Multi-host operation | Replicated process model | Distributed tests and logical soak | Real hosts, WAN faults and operations program |
| Long-duration operation | Controller and logical-clock tests | Early-certification rejection | 30 actual wall-clock days |
| Semantic understanding | Bounded modality organs with OOD abstention | v0.43 audit | Large licensed open-world training |
| Test integrity | No skip/xfail/mock substitution | 21 qualification files scanned; 117/117 pass | Independent laboratory rerun |
| Release hygiene | No raw keys; isolated wheel qualified | Secret scan, manifest and wheel smoke | Signed release pipeline, SBOM and provenance service |
