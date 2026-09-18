# ENTITY Requirements

The controlling public engineering baseline is **SERS-ENTITY-003 v2.2**, containing 172 normative sections.

Key documents:

- `SERS-ENTITY-003_v2.2_COMPLETE_MASTER_ENGINEERING_DESIGN.md` â€” complete master engineering design.
- `SERS-ENTITY-003_BASELINE.json` â€” machine-readable baseline pointer.
- `SERS-ENTITY-002_BASELINE.json` â€” predecessor baseline metadata.
- `SERS-ENTITY-DOMAIN-001_v1.0.md` â€” sovereign domain/device-native presence requirements.
- `CANONICAL_AUTHORITY_HANDOFF_REQUIREMENTS.md` â€” authority/runtime handoff constraints.
- `CROSS_IMPLEMENTATION_COMPATIBILITY.md` â€” integration compatibility invariants.

The public source tree also carries subsystem-local `ENTITY_REQUIREMENTS.md`, `ENTITY_SUBSYSTEM_REQUIREMENTS.md`, and runtime-binding requirement files near their implementations.

A requirement is not considered qualified merely because code exists. ENTITY's engineering chain is:

```text
REQUIREMENT
â†’ DESIGN
â†’ CODE / CONFIGURATION
â†’ TEST
â†’ RESULT
â†’ EVIDENCE
â†’ HASH
â†’ RELEASE
```
