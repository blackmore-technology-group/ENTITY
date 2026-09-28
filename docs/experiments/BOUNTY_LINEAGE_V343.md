# ENTITY v3.4.3 Bounty Lineage Experiment

## Purpose

This experiment tests whether the installed ENTITY v3.4.3 system can record a real external GitHub bounty contribution as an ordinary lineage, provenance, rights and economic event **without changing ENTITY's protocol, schemas, architecture or canonical structure**.

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

- `tools/bounty/` — PowerShell capture, qualification and guarded push tooling
- `docs/experiments/` — experiment procedure
- `evidence/bounty/` — evidence generated from an installed ENTITY run

## Required lineage

The installed system should be asked to represent the following facts using capabilities that already exist in v3.4.3:

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

## Claimant registration and payout gate

A bounty is not economically usable merely because it is visible on GitHub or a bounty marketplace. Before a candidate can reach `READY_FOR_ENTITY_PREPARED`, the preflight must establish a payable claimant chain:

1. The GitHub contributor identity that will create the contribution/PR is identified.
2. That identity is registered with the bounty platform when the platform requires registration.
3. The economic payee is identified as an individual or business.
4. The payout method is ready, verified, or—on direct-payment platforms—the payment arrangement is explicitly confirmed.
5. A non-sensitive platform account/profile reference is captured when available.

The experiment must **never** place bank-account numbers, card information, tax identifiers, government identification, KYC documents, passwords, tokens, recovery codes or similar secrets in the repository or ENTITY evidence bundle.

For the BTG experiment, the intended identity chain is:

```text
GitHub contributor: blackmore-technology-group
        ↓
bounty-platform claimant account
        ↓
economic payee: Blackmore Technology Group Limited where the platform permits business onboarding
        ↓
verified payout rail / confirmed direct-payment arrangement
        ↓
ENTITY provenance + rights + economic evidence
```

Shawn Blackmore may be represented as the human author/authorized representative where supported by the actual evidence. The external project's pre-existing source remains attributed to its actual upstream authors and licence.

`Test-BountyCandidate.ps1` deliberately fails closed if the account or payout path is not ready. A platform listing alone must never be treated as proof that BTG can actually receive payment.

## Evidence states

A bounty record should move through these states only when supported by real evidence:

- `PREPARED` — qualified bounty metadata captured after claimant/payout readiness; no claim that the bounty was earned.
- `ENTITY_RECORDED` — an installed ENTITY export/receipt exists and has been hashed.
- `UPSTREAM_ACCEPTED` — the external project accepted/merged the work.
- `SETTLED` — payment evidence exists.

Do not mark `UPSTREAM_ACCEPTED` or `SETTLED` from an expectation, pending PR, platform listing, or verbal promise.

## Candidate preflight sequence

Before creating a capture, run the qualification tool with the real platform/account state. Example:

```powershell
.\tools\bounty\Test-BountyCandidate.ps1 `
  -Repository "owner/repository" `
  -IssueNumber 123 `
  -ExpectedAmount 500 `
  -ContributorGitHubLogin "blackmore-technology-group" `
  -BountyPlatform "platform-name" `
  -FundingStatus "ESCROW_VERIFIED" `
  -PlatformAccountStatus "VERIFIED" `
  -PayoutStatus "READY" `
  -PayeeType "BUSINESS" `
  -PayeeDisplayName "Blackmore Technology Group Limited" `
  -PlatformAccountReference "public-profile-or-account-reference" `
  -ClaStatus "REVIEWED" `
  -AiContributionPolicy "DISCLOSED_ALLOWED" `
  -OutFile ".\evidence\bounty\candidate-preflight.json"
```

For a platform where the bounty sponsor pays the developer directly rather than through a platform payout rail, use `DIRECT_PAYMENT_CONFIRMED` only after the payment arrangement is actually established. Do not use that value merely because a sponsor is expected to pay.

## Suggested desktop sequence

```powershell
# From the local ENTITY v3.4.3 repository/build workspace.
# Adjust only if the installed v3.4.3 path differs on the desktop.
$repo = "E:\ENTITY_ACTIVE\ENTITY_V3_4_3"
Set-Location $repo

# Only after Test-BountyCandidate.ps1 returns READY_FOR_ENTITY_PREPARED:
.\tools\bounty\New-EntityBountyCapture.ps1 `
  -ExternalRepository "owner/repository" `
  -IssueNumber 123 `
  -BountyPlatform "platform-name" `
  -BountyAmount 500 `
  -Currency "USD" `
  -BountyUrl "https://..." `
  -UpstreamLicense "MIT"

# Run the installed ENTITY v3.4.3 application normally and record the
# contribution through its existing lineage/rights/economic interfaces.
# Export the resulting evidence from ENTITY.
```

After the installed application has produced real evidence, use the guarded push tool. It stages only the selected `evidence/bounty/<record>` directory and refuses to commit unrelated source/protocol changes.

```powershell
.\tools\bounty\Push-EntityBountyEvidence.ps1 `
  -RecordDirectory ".\evidence\bounty\bounty-..." `
  -CommitMessage "evidence: record external bounty lineage through ENTITY v3.4.3"
```

## Rights boundary

The evidence record should describe only rights that can be supported by the upstream licence, contributor terms/CLA, authorship evidence and the ENTITY output. Recording provenance does not override an upstream licence, create ownership that did not exist, or convert upstream project code into BTG-owned code.

## Success condition

The experiment succeeds if a genuine bounty contribution can pass through the installed v3.4.3 system and produce an auditable lineage/right/economic evidence chain while a repository comparison confirms **zero protocol/schema/implementation changes were required for the use case**.
