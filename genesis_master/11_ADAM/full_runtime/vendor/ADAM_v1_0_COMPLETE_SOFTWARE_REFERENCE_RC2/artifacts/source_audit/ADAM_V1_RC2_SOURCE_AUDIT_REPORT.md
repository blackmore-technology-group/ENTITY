# ADAM v1.0 RC2 Mechanical Source-Tree Audit

- Operational Python files scanned: **101**
- Non-Python source files scanned: **27**
- Qualification test files checked for skip/xfail/mock substitution: **21**
- Python compileall: **PASS**
- Blocking open findings: **0**
- Native C framing reference: **compiled and restart-verified**
- Raw secret-file scan: **PASS**
- Rust targets: **2 source targets; 0 compiled here**

## Classification

`pass` statements in exception classes, Protocol ellipses and best-effort cleanup handlers are classified as intentional contracts/no-ops, not runtime stubs. Test-clock guards are retained because they prevent development runs from issuing production certification.

## External gates

- Rust compilation, Miri, fuzzing and reproducible builds require an external Rust toolchain.
- HSM/KMS, multi-host network and real-device qualification require external infrastructure.
- Thirty-day certification requires actual elapsed wall-clock time.

## Findings

| Severity | Category | Status | Location | Finding |
|---|---|---|---|---|
| INFO | source_marker | historical_gap_label | `adam_v41/audit.py:292` | "gap": "Private-key handling is development-only", |
| LOW | broad_exception | review_required | `adam_v41/authority.py:64` | broad exception catch in _atomic_write |
| INFO | pass_statement | intentional_best_effort_cleanup_or_parse | `adam_v41/authority.py:37` | exception intentionally ignored |
| INFO | pass_statement | intentional_best_effort_cleanup_or_parse | `adam_v41/authority.py:57` | exception intentionally ignored |
| LOW | broad_exception | review_required | `adam_v41/authority.py:180` | broad exception catch in _load_private |
| INFO | pass_statement | intentional_best_effort_cleanup_or_parse | `adam_v41/authority.py:194` | exception intentionally ignored |
| INFO | pass_statement | intentional_best_effort_cleanup_or_parse | `adam_v41/authority.py:75` | exception intentionally ignored |
| LOW | broad_exception | review_required | `adam_v41/authority.py:94` | broad exception catch in _decode_kek |
| INFO | pass_statement | intentional_best_effort_cleanup_or_parse | `adam_v41/authority.py:71` | exception intentionally ignored |
| INFO | pass_statement | intentional_exception_class | `adam_v41/log.py:19` | empty class body: LogIntegrityError |
| INFO | pass_statement | intentional_exception_class | `adam_v41/universe.py:17` | empty class body: IntegrityError |
| INFO | pass_statement | intentional_exception_class | `adam_v41/universe.py:21` | empty class body: ConflictError |
| INFO | pass_statement | intentional_exception_class | `adam_v41/universe.py:25` | empty class body: AuthorityError |
| INFO | broad_exception | intentional_error_boundary | `adam_v41/universe.py:584` | broad exception catch in _load_checkpoint |
| INFO | pass_statement | intentional_exception_class | `adam_v42/distributed.py:20` | empty class body: ConsensusError |
| INFO | pass_statement | intentional_exception_class | `adam_v42/embodiment.py:13` | empty class body: EmbodimentError |
| INFO | pass_statement | intentional_exception_class | `adam_v42/erasure.py:10` | empty class body: ErasureError |
| INFO | pass_statement | intentional_exception_class | `adam_v42/evidence.py:12` | empty class body: EvidenceError |
| INFO | pass_statement | intentional_exception_class | `adam_v42/formal.py:12` | empty class body: ProofError |
| INFO | pass_statement | intentional_exception_class | `adam_v42/isolation.py:35` | empty class body: IsolatedKernelError |
| INFO | broad_exception | intentional_error_boundary | `adam_v42/isolation.py:67` | broad exception catch in _server |
| INFO | pass_statement | intentional_best_effort_cleanup_or_parse | `adam_v42/isolation.py:124` | exception intentionally ignored |
| INFO | pass_statement | intentional_exception_class | `adam_v42/key_management.py:19` | empty class body: KeyStoreError |
| INFO | pass_statement | intentional_exception_class | `adam_v42/operations_one.py:23` | empty class body: O1QualificationError |
| INFO | pass_statement | intentional_best_effort_cleanup_or_parse | `adam_v42/perception.py:149` | exception intentionally ignored |
| INFO | pass_statement | intentional_exception_class | `adam_v42/query.py:10` | empty class body: QueryError |
| INFO | pass_statement | intentional_exception_class | `adam_v42/recreation.py:27` | empty class body: RecreationError |
| INFO | broad_exception | intentional_error_boundary | `adam_v42/recreation.py:596` | broad exception catch in verify |
| INFO | pass_statement | intentional_best_effort_cleanup_or_parse | `adam_v42/recreation.py:328` | exception intentionally ignored |
| INFO | pass_statement | intentional_exception_class | `adam_v42/security.py:21` | empty class body: AuthorizationError |
| INFO | broad_exception | intentional_error_boundary | `adam_v42/soak.py:56` | broad exception catch in run_logical_soak |
| INFO | pass_statement | intentional_exception_class | `adam_v43/key_custody.py:41` | empty class body: CustodyError |
| INFO | ellipsis_body | intentional_protocol_contract | `adam_v43/key_custody.py:67` | Protocol method contract |
| INFO | ellipsis_body | intentional_protocol_contract | `adam_v43/key_custody.py:68` | Protocol method contract |
| INFO | ellipsis_body | intentional_protocol_contract | `adam_v43/key_custody.py:69` | Protocol method contract |
| INFO | ellipsis_body | intentional_protocol_contract | `adam_v43/key_custody.py:70` | Protocol method contract |
| INFO | pass_statement | intentional_best_effort_cleanup_or_parse | `adam_v43/key_custody.py:191` | exception intentionally ignored |
| INFO | pass_statement | intentional_exception_class | `adam_v43/production_soak.py:18` | empty class body: QualificationError |
| INFO | broad_exception | intentional_error_boundary | `adam_v43/production_soak.py:193` | broad exception catch in cycle |
| INFO | source_marker | intentional_qualification_guard | `adam_v43/production_soak.py:241` | raise QualificationError("test-only clock can never issue production certification") |
| INFO | pass_statement | intentional_exception_class | `adam_v43/semantic_world.py:16` | empty class body: SemanticError |
| INFO | ellipsis_body | intentional_protocol_contract | `adam_v43/semantic_world.py:22` | Protocol method contract |
| INFO | pass_statement | intentional_exception_class | `adam_v43/temporal_learning.py:16` | empty class body: TemporalLearningError |
| INFO | pass_statement | intentional_best_effort_cleanup_or_parse | `adam_v43/temporal_learning.py:296` | exception intentionally ignored |
| INFO | pass_statement | intentional_exception_class | `adam_v43/theorem_proving.py:14` | empty class body: TheoremError |
| INFO | broad_exception | intentional_error_boundary | `adam_v43/theorem_proving.py:92` | broad exception catch in prove_identity |
| INFO | pass_statement | intentional_exception_class | `adam_v44/authority_service.py:34` | empty class body: AuthorityServiceError |
| INFO | broad_exception | intentional_error_boundary | `adam_v44/authority_service.py:64` | broad exception catch in _serve |
| INFO | pass_statement | intentional_best_effort_cleanup_or_parse | `adam_v44/authority_service.py:124` | exception intentionally ignored |
| INFO | pass_statement | intentional_exception_class | `adam_v44/physics.py:191` | empty class body: PhysicsError |
| INFO | broad_exception | intentional_error_boundary | `adam_v47/world_model.py:91` | broad exception catch in simulate |
| INFO | pass_statement | intentional_exception_class | `adam_v50/distributed_physics.py:14` | empty class body: DistributedPhysicsError |
| INFO | pass_statement | intentional_exception_class | `adam_v50/production_qualification.py:15` | empty class body: QualificationError |
| INFO | broad_exception | intentional_error_boundary | `adam_v50/production_qualification.py:114` | broad exception catch in run_cycle |
| INFO | source_marker | intentional_qualification_guard | `adam_v50/production_qualification.py:157` | raise QualificationError("test-only qualification cannot certify production") |
| INFO | ellipsis_body | intentional_protocol_contract | `adam_v52/custody.py:91` | Protocol method contract |
| INFO | ellipsis_body | intentional_protocol_contract | `adam_v52/custody.py:92` | Protocol method contract |
| INFO | ellipsis_body | intentional_protocol_contract | `adam_v52/custody.py:93` | Protocol method contract |
| INFO | ellipsis_body | intentional_protocol_contract | `adam_v52/custody.py:94` | Protocol method contract |
| INFO | ellipsis_body | intentional_protocol_contract | `adam_v52/custody.py:95` | Protocol method contract |
| INFO | ellipsis_body | intentional_protocol_contract | `adam_v52/custody.py:96` | Protocol method contract |
| INFO | ellipsis_body | intentional_protocol_contract | `adam_v52/custody.py:97` | Protocol method contract |
| INFO | ellipsis_body | intentional_protocol_contract | `adam_v52/custody.py:98` | Protocol method contract |
| INFO | ellipsis_body | intentional_protocol_contract | `adam_v52/custody.py:99` | Protocol method contract |
| INFO | ellipsis_body | intentional_protocol_contract | `adam_v52/custody.py:100` | Protocol method contract |
| LOW | broad_exception | review_required | `adam_v52/custody.py:396` | broad exception catch in provision |
| LOW | broad_exception | review_required | `adam_v52/key_material.py:58` | broad exception catch in load_or_create_master_key |
| LOW | broad_exception | review_required | `adam_v52/key_material.py:104` | broad exception catch in load_or_create_ed25519_private_key |
| INFO | pass_statement | intentional_best_effort_cleanup_or_parse | `adam_v52/key_material.py:18` | exception intentionally ignored |
| INFO | pass_statement | intentional_best_effort_cleanup_or_parse | `adam_v52/key_material.py:62` | exception intentionally ignored |
| INFO | pass_statement | intentional_best_effort_cleanup_or_parse | `adam_v52/key_material.py:66` | exception intentionally ignored |
| INFO | pass_statement | intentional_best_effort_cleanup_or_parse | `adam_v52/key_material.py:108` | exception intentionally ignored |
| INFO | pass_statement | intentional_best_effort_cleanup_or_parse | `adam_v52/key_material.py:112` | exception intentionally ignored |
| INFO | source_marker | historical_gap_label | `adam_v52/key_material.py:17` | # development-only software-custody fallback, never an HSM claim. |
| INFO | ellipsis_body | intentional_protocol_contract | `adam_v54/device_pilot.py:108` | Protocol method contract |
| INFO | ellipsis_body | intentional_protocol_contract | `adam_v54/device_pilot.py:109` | Protocol method contract |
| INFO | ellipsis_body | intentional_protocol_contract | `adam_v54/device_pilot.py:110` | Protocol method contract |
| LOW | broad_exception | review_required | `run_v1_local_qualification.py:43` | broad exception catch in gate |
| INFO | pass_statement | intentional_best_effort_cleanup_or_parse | `run_v1_local_qualification.py:244` | exception intentionally ignored |
| INFO | broad_exception | intentional_error_boundary | `run_v42_audit.py:51` | broad exception catch in check |
| INFO | pass_statement | intentional_best_effort_cleanup_or_parse | `run_v42_audit.py:218` | exception intentionally ignored |
| INFO | broad_exception | intentional_error_boundary | `run_v42_living_recreation_audit.py:57` | broad exception catch in check |
| INFO | broad_exception | intentional_error_boundary | `run_v43_gap_closure_audit.py:43` | broad exception catch in check |
| INFO | broad_exception | intentional_error_boundary | `run_v50_full_audit.py:30` | broad exception catch in check |
| INFO | broad_exception | intentional_error_boundary | `tools/audit_source_tree.py:200` | broad exception catch in compile_c_reference |
| INFO | broad_exception | intentional_error_boundary | `tools/audit_source_tree.py:275` | broad exception catch in rust_targets |
| LOW | broad_exception | review_required | `tools/generate_v1_rc2_sbom.py:47` | broad exception catch in main |
| INFO | source_marker | historical_gap_label | `tools/verify_release_manifest.py:84` | parser.add_argument("--allow-unsigned", action="store_true", help="development-only; never use for a sealed release") |
| EXTERNAL | rust_target | external_toolchain_required | `rust_authority_kernel/src/main.rs:1` | cargo/rustc unavailable; source static-audited only |
| EXTERNAL | rust_target | external_toolchain_required | `rust_authority_kernel_v44/src/main.rs:1` | cargo/rustc unavailable; source static-audited only |
| MEDIUM | placeholder_or_overbroad_claim | review_required | `ADAM_V051_ENGINEERING_CONTRACT.md:8` | - Promotion target: **ADAM v0.51 — Compiled Authority and Information-Physics Kernel** |
| MEDIUM | placeholder_or_overbroad_claim | review_required | `ADAM_V051_EXTERNAL_RUST_ACCEPTANCE.md:90` | Only that bundle can change the release name to **ADAM v0.51 — Compiled Authority and Information-Physics Kernel**. |
