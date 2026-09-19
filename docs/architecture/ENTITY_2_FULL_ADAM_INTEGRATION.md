# ENTITY 2.0 Development - Full ADAM v1.0 Integration

ENTITY Protocol 1.0 remains frozen for external conformance. This document defines the development boundary for the next major line because full ADAM integration expands evidence and state-transition semantics and must not be silently backported into Protocol 1.0.

## Authority model

- **ENTITY**: sovereign identity, delegated authority, rights, policy, consent, contracts, usage and portability.
- **ADAM**: deterministic atomic information, exact evidence and reconstruction, reaction-governed state transitions, historical continuity and bounded ADAM runtime evidence.
- **NIKI**: reasoning, interpretation, uncertainty and action proposals only.
- **BSIE**: spatial/world representation within its governed scope.

The invariant is `execution_authority = ENTITY`, `executor = ADAM`, `reasoner = NIKI`. ADAM never self-grants ENTITY authority and NIKI never acquires ADAM mutation authority.

## Integrated ADAM surfaces

The implementation bridge is designed against the complete ADAM v1.0 RC2 bounded software reference, including the atomic universe, exact object reconstruction, evidence alignment, reaction history, cognition/application/runtime surfaces, custody/reference authority mechanisms and bounded distributed-authority facilities exposed by that release.

ENTITY-authorized transitions are serialized as exact ADAM evidence, aligned to a semantic transition claim, then committed through an ADAM reaction. The resulting receipt records the pre/post roots, sequence transition, evidence object, claim proof and reaction proof.

NIKI receives metadata-minimized ADAM projections only. Raw evidence bytes, private keys, credentials and vault locators are not projected by this bridge.

## ADAM package pin

The integration pins `ADAM_v1_0_COMPLETE_SOFTWARE_REFERENCE_RC2.zip` at SHA-256 `3cc6541f2d00dd0580989cc7fe6e8abd56974d1069f61c710e230568e00b8da3`. The public ENTITY source tree does not redistribute the ADAM package. A verified ADAM source root is supplied with `ENTITY_ADAM_V1_ROOT`.

## Qualification boundary

BTG software qualification for the bridge does not close ADAM external gates such as hardware HSM/KMS custody, physically independent multi-host deployment, certified device pilots, large licensed real-world training, thirty actual wall-clock days or an independent security/safety/operations audit. ENTITY independent non-BTG interoperability remains a separate external proof gate.
