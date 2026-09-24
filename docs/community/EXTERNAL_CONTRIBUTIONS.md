# ENTITY External Contribution Ledger

This ledger records attributable work contributed by people or organizations outside Blackmore Technology Group Limited (BTG) control.

It exists to recognize real external participation **without overstating what the participation proves**. An external bug report, documentation improvement or portability result is an external contribution; it is not automatically an independent implementation, interoperability result, security audit, certification or endorsement.

## Recorded contributions

| Date | Contributor | Project / target | Contribution | Public evidence | Evidence class | Claim boundary |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-09-23 to 2026-09-24 | [@kant2002](https://github.com/kant2002) | ENTITY Protocol 1.0 Conformance Kit | Independently attempted the public developer workflow inside a local `.venv`, identified that kit validation recursively treated virtual-environment packages as prohibited implementation files, and supplied reproducible commands/output. The report led to the v1.0.2 developer-mode fix while preserving strict worktree verification for CI/sealed validation. | [Issue #6](https://github.com/blackmore-technology-group/ENTITY-Protocol-1.0-Conformance-Kit/issues/6), [fix PR #7](https://github.com/blackmore-technology-group/ENTITY-Protocol-1.0-Conformance-Kit/pull/7), main merge `905c309d2461ad192514bfd356527119f134739b` | External defect / developer-workflow / portability report | This is real outside participation and a reproduced defect report. It is **not** claimed as independent protocol conformance, independent interoperability, third-party security validation or endorsement of ENTITY. |

## Why this contribution matters

The Protocol 1.0 kit is deliberately designed to be exercised by unrelated implementers. The `.venv` report exposed a real developer-workflow defect that BTG-controlled qualification had not surfaced in the same way.

The correct response was not to dismiss the environment difference or weaken the sealed target. The maintenance fix separated ordinary developer workflow from strict sealed-worktree verification:

- recognized top-level `.venv` / `venv` environments are ignored in normal developer validation when they are genuine Python virtual environments;
- `--strict-worktree` retains strict verification for CI and sealed qualification;
- protocol semantics, schemas, vectors and pass criteria were not changed to make the test easier.

That is exactly the kind of external feedback this project wants: a concrete reproduction that improves the public engineering surface.

## What will be recorded here

Future entries may include:

- reproducible external bug reports that materially change the project;
- external portability or environment reproductions;
- merged external pull requests;
- specification ambiguities or counterexamples;
- independently authored benchmarks;
- independently authored clean-room implementations;
- conformance/interoperability results;
- independently authored security-review findings after disclosure requirements are satisfied.

Each entry should identify the **actual evidence class** and its **claim boundary**.

## What will not be inferred

An entry in this ledger does not by itself mean that the contributor:

- endorses ENTITY or BTG;
- works for or represents BTG;
- independently validated the whole protocol;
- completed live interoperability;
- performed a security audit;
- made a legal, regulatory or certification determination.

Those stronger milestones require their own evidence and are tracked separately where appropriate, including the [Interoperability Status](../interoperability/STATUS.md) and [Independent Security Review Program](../security/INDEPENDENT_SECURITY_REVIEW_PROGRAM.md).

## Corrections or attribution preferences

If a contributor wants an attribution corrected, scoped differently or removed from BTG-authored recognition text, open a documentation issue or use an appropriate private company channel where privacy is involved. Underlying public GitHub issue/commit history remains governed by GitHub and the repositories in which that activity occurred.
