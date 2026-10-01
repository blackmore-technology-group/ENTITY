# ENTITY Interoperability Challenge

**Document class:** external engineering challenge / non-normative orientation  
**Current supported runtime:** ENTITY v3.4.3  
**Frozen Protocol 1.0 target:** ENTITY Protocol 1.0 External Conformance Kit v1.0.2  
**Frozen BTG language campaign discussed below:** ENTITY v3.4.2 26-vector target

ENTITY is looking for engineers who want to test the protocol, not merely endorse it.

The strongest question is:

> **Can an unrelated implementation reproduce the required ENTITY Protocol 1.0 semantics from the permitted public material, interoperate bidirectionally with BTG, and survive the required sovereign export/recovery path?**

BTG already maintains controlled cross-language baselines. Those are useful engineering evidence, but they are not independently authored external implementations. External reproduction of those baselines is meaningful reproduction evidence, but it is still a different evidence class from an independent implementation.

Read [Documentation Model](DOCUMENTATION_MODEL.md) before choosing a target so that current runtime, frozen campaign and Protocol 1.0 material are not mixed.

## Evidence ladder

### Level 0 — Reproduce an exact published target

Typical work:

- pin the exact release/kit/commit;
- run documented verification/tests;
- reproduce a published vector outcome or hash;
- report environment-specific failures or documentation ambiguity.

A clean reproduction report is useful evidence. It must identify exactly what was reproduced.

For example, reproducing the BTG-controlled v3.4.2 26-vector Java campaign is **external reproduction** of that campaign. It is not automatically an independently designed Protocol 1.0 implementation.

### Level 1 — Challenge one semantic boundary

Choose one area and try to break or clarify it:

- canonicalization/signature behavior;
- identity/root versus alias semantics;
- authority/delegation/revocation;
- provider custody versus sovereign authority;
- rights and entitlement boundaries;
- invalid/tampered vector rejection;
- evidence versus external-world truth;
- external-anchor non-authority;
- dispute/supersession history;
- portability/recovery behavior.

A counterexample, missing test or ambiguous rule is a successful result if it improves the specification or implementation guidance.

### Level 2 — Build a small independent clean-room candidate

Implement a narrow public interface in a language/runtime of your choice using only the material permitted by the chosen clean-room campaign.

Useful ecosystems include Rust, Go, C#/.NET, TypeScript, Java/Kotlin, Swift and others. The language is less important than genuine independence of authorship/control.

Your architecture, dependencies, repository structure, testing strategy and internal design are yours.

### Level 3 — Independent Protocol 1.0 conformance

A candidate seeking independent Protocol 1.0 qualification should:

1. Pin the exact sealed Protocol 1.0 release/kit.
2. Document the clean-room boundary.
3. Implement the required public candidate interface.
4. Accept all required valid vectors.
5. Reject all required invalid/tampered vectors.
6. Publish implementation and CI evidence independently.
7. Preserve the required protocol interpretations without BTG implementation code.

BTG can clarify published specification/vector intent but should not author the candidate and later call it independent.

### Level 4 — Independent live interoperability and recovery

The stronger milestone requires the independently controlled candidate to complete the applicable live interoperability and sovereign export/recovery gates, including:

- BTG → independent communication;
- independent → BTG communication;
- sovereign export verification;
- recovery/survival test;
- same required protocol interpretation after recovery;
- independently authored evidence/report.

Until those gates are completed, report the exact partial scope rather than calling the result full external interoperability.

## Protocol 1.0 clean-room target

The authoritative independent clean-room starting point is the separately maintained [ENTITY Protocol 1.0 External Conformance Kit](https://github.com/blackmore-technology-group/ENTITY-Protocol-1.0-Conformance-Kit).

It contains the public protocol/profile material, schemas, trust material, vectors, candidate interface, pass criteria, interoperability procedure and evidence templates needed for that frozen target.

**BTDU, ADAM, NIKI and later ENTITY runtime internals are not additional Protocol 1.0 implementation requirements unless the sealed Protocol 1.0 material explicitly says so.**

Questions about Protocol 1.0 semantics are welcome. Questions that require inspecting/copying BTG reference implementation internals are outside the clean-room boundary.

## Current runtime versus frozen campaign targets

ENTITY v3.4.3 is the current supported BTG runtime. BTDU remains component version 3.4.2 unchanged.

The public BTG-controlled language repositories also deliberately retain a **frozen v3.4.2 26-vector campaign** with:

- 26/26 expected PASS;
- sealed-kit SHA-256 `ced70113f1d153627eb972b11adbf20e502ed086e0b13e8abf1dc5adc4c2e716`;
- canonical result SHA-256 `45af773554a7191c1b49a75c636a1106afb1de36d788bb00d7af56097b8d1b0e`;
- `overall_valid: true`.

The v3.4.2 label identifies that exact frozen evidence target. It is **not** a statement that v3.4.2 remains the current supported runtime.

BTG-controlled baselines exist in:

**Rust · TypeScript · C#/.NET · Go · Swift · Java**

They remain BTG-controlled evidence even when implemented in different languages.

## External reproduction already demonstrated

An unrelated GitHub contributor has reproduced the published BTG-controlled Java v3.4.2 26-vector baseline with exact expected hashes and `overall_valid: true`.

That materially strengthens reproducibility/portability evidence. It still does not by itself establish:

- independently authored Protocol 1.0 implementation;
- bidirectional independent interoperability;
- sovereign recovery by an independently controlled implementation;
- independent security certification or broader deployment claims.

## What counts as independent?

For independent implementation evidence, independence is about control and authorship, not merely programming language.

A strong attempt should:

- be authored outside BTG control;
- live in a repository controlled by the unrelated implementer/organization;
- avoid copying/porting BTG implementation code;
- identify the exact permitted public specification/kit;
- choose its own architecture/libraries/implementation approach;
- publish failures as well as successes;
- author its own final evidence/qualification report.

## Claim boundaries remain in force

Independent testing does not alter ENTITY's ownership/economic boundaries:

```text
UPSTREAM OWNERSHIP
        ≠
BTG FORK CUSTODY
        ≠
BTG-CREATED ENTITY METADATA OWNERSHIP
        ≠
ENTITY PROTOCOL ORIGIN
        ≠
AUTOMATIC ECONOMIC RIGHTS
```

A reproduction, ingest, registration, signature or provenance record proves only the bounded fact it actually verifies.

## Credit

Independent implementers and meaningful external contributors should be credited publicly with links to their own repositories/evidence when they choose to participate publicly.

Partial results matter. A developer who identifies a real ambiguity, breaks a vector assumption, documents a portability problem or produces an independent subset implementation has improved the credibility of the project even before full interoperability is reached.

## Questions

Questions about scope and public semantics are welcome. If a task looks large, open a discussion or issue so it can be narrowed into a useful independently owned piece of work without BTG taking over the implementation.
