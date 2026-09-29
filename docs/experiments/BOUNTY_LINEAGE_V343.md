# ENTITY v3.4.3 Contribution-Value Lineage Experiment

## Purpose

This experiment tests whether the installed ENTITY v3.4.3 system can record real external GitHub contributions as ordinary lineage, provenance, rights and economic/reputational events **without changing ENTITY's protocol, schemas, architecture or canonical structure**.

The experiment is evidence-only. It does not introduce a bounty protocol, new ENTITY object type, new rights model, new settlement model, or replacement economic structure.

The campaign intentionally covers more than prepaid bounties. External contributions are classified into three broad economic states:

- **FUNDED / SETTLED** — a cash-backed bounty or paid contribution. Monetary value is recognized only when the supporting funding/settlement evidence exists.
- **PROMISED / CONTINGENT** — payment is advertised or promised but funding is not verified. The amount may be preserved as contingent opportunity value, but must not be represented as settled revenue or guaranteed payment.
- **PRO_BONO / FREE ISSUE** — no monetary reward. The contribution can still create auditable provenance, upstream acceptance, contribution history, technical validation, reputation/visibility evidence and reusable knowledge where permitted. Realized cash value remains zero unless a later economic event occurs.

The larger hypothesis is:

```text
external problem
    ↓
Blackmore contribution
    ↓
verifiable change-set + authorship
    ↓
ENTITY provenance / rights record
    ↓
external validation or merge
    ↓
economic, reputational or technical consequence
```

## Locked boundary

The following directories are outside the scope of this experiment and must not be modified for the campaign:

- `protocol/`
- `src/`
- `sdk/`
- `profiles/`
- `tests/`
- release manifests and release metadata

GitHub preparation is limited to:

- `tools/bounty/` — PowerShell capture, qualification and guarded push tooling
- `docs/experiments/` — experiment procedure
- `evidence/bounty/` — public evidence generated from installed ENTITY runs

The existing `evidence/bounty/` path remains the experiment umbrella even when a selected issue is pro-bono. No ENTITY structure change is required merely to distinguish economic states.

## Required lineage

The installed system should be asked to represent the following facts using capabilities that already exist in v3.4.3:

1. External platform, repository and issue identifier.
2. External source/repository state before the contribution.
3. Human contribution authorship.
4. Blackmore Technology Group Limited corporate contribution/economic participation where applicable.
5. Work-product hashes, commits and pull-request evidence.
6. Applicable upstream licence and contributor agreement status.
7. Rights/provenance represented by the installed ENTITY system.
8. External maintainer acceptance, rejection or merge status.
9. Actual economic state: funded, promised/contingent, zero-dollar, earned, paid or otherwise evidenced.
10. ENTITY export/receipt/seal produced by the installed system.

No field in the capture harness substitutes for an ENTITY record. The PowerShell files only preserve inputs and hashes around the installed application so that the final evidence can be audited.

## Portable public evidence rule

Installed ENTITY/BTDU receipts may contain machine-local operational paths. The original sealed receipt bytes remain authoritative in the local evidence archive and are identified by their SHA-256 and ENTITY/BTDU lineage.

A path-bearing sealed receipt must **not** be committed directly to the public repository. Instead publish a portable public projection that:

- identifies itself as a projection rather than the sealed receipt;
- records the exact sealed receipt SHA-256 and sealed receipt schema;
- preserves the relevant atomic root, predecessor hash and external contribution identifiers;
- preserves the actual upstream acceptance/review/CI/economic state;
- omits workstation-local paths and other non-portable operational fields;
- states that the sealed receipt remains unchanged and authoritative.

The public projection does not re-seal, rewrite or replace the original receipt. It is a portable evidence view anchored to the immutable sealed receipt hash.

## Candidate policy

Funding status is **not** a universal rejection gate.

A contribution opportunity may proceed if it is useful to at least one campaign objective and passes the hard repository, rights and safety gates.

### Hard gates for every candidate

- upstream GitHub issue/repository state is current and independently verified;
- repository is legitimate and sufficiently active for the proposed work;
- licence and contribution terms are identified;
- CLA/DCO/signing requirements are understood before submission;
- no private prompts, credentials, secrets or unrelated proprietary material must be disclosed;
- scope is technically achievable and not deceptive or spammy;
- upstream code remains attributed to its actual authors and licence;
- AI-assistance requirements, if any, can be complied with;
- no false claim of payment, ownership, acceptance or settlement is created.

### Commercial track

When immediate cash revenue is the objective, prefer funded/escrowed work with a verified claimant and payout path. `SETTLED` requires real payment evidence.

### Promised / contingent track

Promised-only work may proceed when the technical, proof or visibility value justifies it. Preserve the advertised amount and source of the promise, but treat realized cash as zero until payment actually occurs.

### Pro-bono proof / traffic track

A zero-dollar issue may proceed when it offers meaningful external validation, a useful contribution, strong provenance evidence, relevant GitHub contribution history, technical relevance or legitimate visibility. Monetary realized value remains zero unless a later economic event occurs.

## Value model

Each accepted contribution can create several different forms of value. These must remain distinguishable:

- **cash value** — money actually funded/earned/settled;
- **contingent value** — promised or conditional consideration that has not settled;
- **provenance value** — independently verifiable evidence of who changed what and when;
- **validation value** — acceptance/merge/test evidence from an unrelated project;
- **reputation/contribution value** — public contribution history attributable to the contributor identity;
- **traffic/discovery value** — legitimate public paths through which outside developers can discover BTG/ENTITY, subject to the upstream project's norms;
- **knowledge/IP value** — reusable know-how or independently developed BTG material where the upstream licence and contribution terms permit it.

ENTITY should record the evidence and consequence; it must not convert one value class into another merely because the evidence exists.

## Claimant registration and payout gate

For paid work, establish a payable claimant chain before treating the task as a commercial candidate:

1. GitHub contributor identity is identified.
2. Platform registration is complete if required.
3. Economic payee is identified as an individual or business.
4. Payout method is ready/verified, or direct-payment arrangement is explicitly confirmed.
5. A non-sensitive platform account/profile reference is captured when available.

The experiment must **never** place bank-account numbers, card information, tax identifiers, government identification, KYC documents, passwords, tokens, recovery codes or similar secrets in the repository or ENTITY evidence bundle.

For BTG the intended identity chain is:

```text
GitHub contributor: blackmore-technology-group
        ↓
external contribution / bounty platform where applicable
        ↓
economic payee: Blackmore Technology Group Limited where permitted
        ↓
ENTITY provenance + rights + consequence evidence
```

Shawn Blackmore may be represented as the human author/authorized representative where supported by the actual evidence. The external project's pre-existing source remains attributed to its actual upstream authors and licence.

## Evidence states

The existing evidence states remain conservative:

- `PREPARED` — candidate metadata captured; no claim that money was earned.
- `ENTITY_RECORDED` — installed ENTITY export/receipt exists and has been hashed.
- `UPSTREAM_ACCEPTED` — external project accepted/merged the work.
- `SETTLED` — payment evidence exists.

For promised-only and pro-bono work, `UPSTREAM_ACCEPTED` can be a valid terminal experiment result even if `SETTLED` never occurs.

Do not mark `UPSTREAM_ACCEPTED` or `SETTLED` from an expectation, pending PR, marketplace listing or verbal promise.

## Current external proof state

As of 2026-09-29, the experiment has two completed unrelated upstream acceptance cases published as portable public projections:

- Vector issue `#26501` / PR `#26504` — merged and recorded as upstream accepted; PRO_BONO; realized cash `0 USD`.
- Memnox issue `#46` / PR `#86` — merged after maintainer review/change and recorded as upstream accepted; PRO_BONO; realized cash `0 USD`.

AWS issue `#934` / PR `#935` is an active third external case. The contribution is open at the recorded head with local validation green, while AWS Build and OTel Conformance workflows remain dependent on upstream maintainer workflow approval. It must remain below `UPSTREAM_ACCEPTED` until AWS produces actual acceptance/merge evidence.

## Desktop validation sequence

```powershell
# Work from the verified installed ENTITY v3.4.3 repository/build workspace.
# On this machine the active repository may retain an older directory name;
# verify by Git branch/release contents rather than renaming the directory.

# For a paid candidate, use the existing bounty preflight and capture tooling.
# For promised or pro-bono candidates, preserve the actual monetary state and
# never mark SETTLED unless real payment evidence later exists.
```

For every selected candidate:

1. Verify the live upstream issue and repository.
2. Classify it as funded/paid, promised/contingent, or pro-bono.
3. Capture licence, CLA/DCO and contribution-policy evidence.
4. Preserve the pre-work source/issue state and hashes where practical.
5. Perform the contribution in the upstream project, not inside ENTITY.
6. Preserve commit/PR/test evidence.
7. Run installed ENTITY v3.4.3 normally and record the contribution through existing lineage/rights/economic interfaces.
8. Export/receipt/seal the resulting ENTITY evidence.
9. Publish only portable public evidence; keep path-bearing sealed receipts in the local evidence archive.
10. Mark `UPSTREAM_ACCEPTED` only after independent upstream acceptance/merge evidence.
11. Mark `SETTLED` only after actual payment evidence.
12. Confirm no ENTITY protocol/schema/implementation change was required.

## Rights boundary

The evidence record should describe only rights that can be supported by the upstream licence, contributor terms/CLA, authorship evidence and ENTITY output. Recording provenance does not override an upstream licence, create ownership that did not exist, convert upstream project code into BTG-owned code, or transform a promise into earned revenue.

## Success condition

The experiment succeeds if real external GitHub contributions—paid, promised or pro-bono—can pass through installed ENTITY v3.4.3 and produce an auditable chain from external issue → authorship/contribution → ENTITY provenance/rights → external validation → actual economic/reputational consequence, while a repository comparison confirms **zero protocol/schema/implementation changes were required for the use case**.
