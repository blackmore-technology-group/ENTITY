# ENTITY v3.4.2 Bounty Lineage Experiment

## Purpose

This experiment tests whether the installed ENTITY v3.4.2 system can record a real external GitHub bounty contribution as an ordinary lineage, provenance, rights and economic event **without changing ENTITY's protocol, schemas, architecture or canonical structure**.

The experiment is evidence-only. It does not introduce a bounty protocol, new ENTITY object type, new rights model, new settlement model, or replacement economic structure.

## Locked boundary

The following directories are outside the scope of this experiment and must not be modified for the bounty test:

- `protocol/`
- `src/`
- `sdk/`
- `profiles/`
- `tests/`
- release manifests and release metadata

The GitHub preparation for the experiment is limited to:

- `tools/bounty/` — PowerShell capture and guarded push tooling
- `docs/experiments/` — experiment procedure
- `evidence/bounty/` — evidence generated from an installed ENTITY run

## Required lineage

The installed system should be asked to represent the following facts using capabilities that already exist in v3.4.2:

1. External bounty platform and bounty/issue identifier.
2. External repository and source state.
3. Human contribution authorship.
4. Blackmore Technology Group Limited corporate contribution/economic participation where applicable.
5. Work-product hashes, commit and pull-request evidence.
6. Applicable upstream licence and contributor agreement status.
7. Rights/provenance represented by the installed ENTITY system.
8. External maintainer acceptance or merge status.
9. Bounty/payment status and economic consequence when actually earned.
10. ENTITY export/receipt/seal produced by the installed system.

No field in the capture harness substitutes for an ENTITY record. The PowerShell files only preserve inputs and hashes around the installed application so that the final evidence can be audited.

## Evidence states

A bounty record should move through these states only when supported by real evidence:

- `PREPARED` — metadata captured; no claim that the bounty was earned.
- `ENTITY_RECORDED` — an installed ENTITY export/receipt exists and has been hashed.
- `UPSTREAM_ACCEPTED` — the external project accepted/merged the work.
- `SETTLED` — payment evidence exists.

Do not mark `UPSTREAM_ACCEPTED` or `SETTLED` from an expectation, pending PR, platform listing, or verbal promise.

## Suggested desktop sequence

```powershell
# From the local ENTITY repository.
$repo = "E:\ENTITY_ACTIVE\ENTITY_V3_4_2_BTDU"
Set-Location $repo

# Capture the bounty before/while working it.
.\tools\bounty\New-EntityBountyCapture.ps1 `
  -ExternalRepository "owner/repository" `
  -IssueNumber 123 `
  -BountyPlatform "platform-name" `
  -BountyAmount 500 `
  -Currency "USD" `
  -BountyUrl "https://..." `
  -UpstreamLicense "MIT"

# Run the installed ENTITY v3.4.2 application normally and record the
# contribution through its existing lineage/rights/economic interfaces.
# Export the resulting evidence from ENTITY.

# Re-run the capture command with the actual export path, or use the path
# printed by the first run and update that record with verified evidence.
```

After the installed application has produced real evidence, use the guarded push tool. It stages only the selected `evidence/bounty/<record>` directory and refuses to commit unrelated source/protocol changes.

```powershell
.\tools\bounty\Push-EntityBountyEvidence.ps1 `
  -RecordDirectory ".\evidence\bounty\bounty-..." `
  -CommitMessage "evidence: record external bounty lineage through ENTITY v3.4.2"
```

## Rights boundary

The evidence record should describe only rights that can be supported by the upstream licence, contributor terms/CLA, authorship evidence and the ENTITY output. Recording provenance does not override an upstream licence, create ownership that did not exist, or convert upstream project code into BTG-owned code.

## Success condition

The experiment succeeds if a genuine bounty contribution can pass through the installed v3.4.2 system and produce an auditable lineage/right/economic evidence chain while a repository comparison confirms **zero protocol/schema/implementation changes were required for the use case**.
