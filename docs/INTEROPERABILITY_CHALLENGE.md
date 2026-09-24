# ENTITY Interoperability Challenge

ENTITY is looking for engineers who want to test the protocol, not merely endorse it.

The central question is:

> **Can an unrelated implementation reproduce ENTITY's authority, rights, evidence and economic-state semantics from public materials alone?**

BTG already maintains controlled cross-language baselines. Those are useful engineering evidence, but they are not independent external validation. This challenge exists to cross that boundary.

## You can start small

A full independent implementation is a substantial systems task. It is **not** the required entry point.

### Level 0 — Reproduce

Typical effort: minutes to a few hours.

- clone the repository or sealed conformance kit;
- run documented verification/tests;
- reproduce one published hash or vector outcome;
- report environment-specific failures or documentation ambiguity.

A clean reproduction report is a useful contribution.

### Level 1 — Challenge one semantic boundary

Typical effort: a few hours.

Choose one area and try to break or clarify it:

- canonicalization/signature behavior;
- identity versus alias/account semantics;
- provider custody versus sovereign authority;
- rights and entitlement boundaries;
- invalid/tampered vector rejection;
- v3.3 truth-state transitions;
- scoped attestation authority;
- external-anchor non-authority;
- dispute/supersession history;
- causal-economic graph evidence requirements.

A counterexample, missing test or ambiguous rule is a successful result if it improves the specification.

### Level 2 — Build a small clean-room candidate

Implement a narrow public interface in a language/runtime of your choice using only the permitted public material for the campaign.

Useful ecosystems include Rust, Go, C#/.NET, TypeScript, Java/Kotlin, Swift and others. The language is less important than genuine implementation independence.

Your architecture, dependencies, repository structure, testing strategy and internal design are yours.

### Level 3 — Full independent conformance

A candidate seeking independent qualification should ultimately:

1. Pin the exact public ENTITY release / sealed kit used.
2. Document the clean-room boundary.
3. Implement the required public candidate interface.
4. Accept all valid campaign vectors.
5. Reject all invalid/tampered campaign vectors.
6. Publish its implementation and CI evidence independently.
7. Complete bidirectional live interoperability with BTG.
8. Complete sovereign export/recovery survival testing.
9. Re-verify the authoritative result after recovery.
10. Publish an independently authored qualification report.

BTG should not write the candidate or its final qualification report.

---

## v3.3 challenge: signed is not the same as true

ENTITY v3.3 makes a specific distinction that is worth attacking independently:

```text
Cryptographic verification
        ≠
Protocol verification
        ≠
Reality/evidence verification
```

An external implementation should be able to distinguish, for example:

- a correctly signed assertion from an externally verified claim;
- a valid evidence object from a claim whose evidence is insufficient for a stronger state;
- a scoped attestation authority from general sovereign authority;
- an external registry snapshot from ENTITY authority;
- a disputed claim from a deleted/rewritten claim;
- a provenance edge from an evidence-backed causal-economic edge.

The design target is not universal truth. The design target is attributable, contestable and machine-verifiable evidence about claims.

---

## What counts as independent?

For external evidence, independence is about control and authorship, not merely programming language.

A strong independent attempt should:

- be authored outside BTG control;
- live in a repository controlled by the independent implementer/organization;
- avoid copying or porting BTG implementation code;
- identify the exact allowed public specification/kit;
- choose its own architecture/libraries/implementation approach;
- publish failures as well as successes;
- author its own final evidence/qualification report.

BTG can answer questions about the public specification, expected vector intent and interoperability procedure without taking over the implementation.

---

## Current controlled baselines

The protected v3.2 release has BTG-controlled native baselines in:

**Rust · TypeScript · C# · Go · Swift · Java**

They converge on documented v3.2 result SHA-256:

`1eb59e09ab08da86bfd8584df4a64ba331f7bbbce3d236b9b94f351606c90e18`

That means an external implementer is not being asked whether cross-language implementation is possible in principle. The stronger question is whether someone **outside BTG** can reach the same semantics without relying on BTG implementation code.

The v3.3 release campaign adds the verifiable-reality/evidence layer to that challenge after its protected public release is sealed.

---

## Protocol 1.0 clean-room campaign

The separately maintained [ENTITY Protocol 1.0 External Conformance Kit](https://github.com/blackmore-technology-group/ENTITY-Protocol-1.0-Conformance-Kit) remains the frozen target for Protocol 1.0 independent campaigns.

That repository contains the public protocol, schemas, profiles, trust material, vectors, black-box runner, interoperability procedure and evidence templates without the BTG reference runtime.

If you want a bounded clean-room starting point today, that kit is the established external campaign surface.

---

## Credit

Independent implementers and meaningful external contributors should be credited publicly with links to their own repositories/evidence when they choose to participate publicly.

Partial results matter. A developer who identifies a real ambiguity, breaks a vector assumption, documents a portability problem, or produces a clean independent subset implementation has contributed to the credibility of the protocol even before full interoperability is reached.

## Questions

Questions about scope and public semantics are welcome. If the task you are considering is large, open a discussion or issue first so it can be narrowed into a useful, independently owned piece of work.
