# Blackmore Technology Group ENTITY Treasury — Deployment Requirements

Status: RELEASED / BTG INTERNAL QUALIFIED / ACTIVATION GATE

The BTG treasury is a deployment of the issuer-neutral ENTITY Originator Participation Profile. It is not a special protocol account and receives no compulsory fee from unrelated ENTITY activity.

## Required identities before activation
1. A verified ENTITY identity representing Blackmore Technology Group as the legal/operating originator.
2. A distinct verified ENTITY identity representing the BTG ENTITY Treasury.
3. Authority evidence permitting the BTG legal ENTITY to establish treasury and issuance policies.
4. A treasury governance-policy document whose SHA-256 is stored in the treasury record.
5. The BTG legal ENTITY and BTG Treasury ENTITY MUST be distinct identifiers.
6. Any independent settlement verifier must be explicitly authorized by the BTG treasury owner before it may mark obligations settled.

The implementation deliberately contains no preselected BTG ENTITY identifier. An uncertain personal, test or legacy ENTITY identifier MUST NOT be silently substituted.

## Value channels supported
- EEP rights-unit treasury reserves;
- allocations from BTG primary rights issuance;
- contractual royalties on permitted secondary transfers;
- contractual participation in derivative commercial revenue;
- BTG-operated venue/listing/execution/clearing/settlement services;
- market-data products;
- certification/conformance services;
- managed infrastructure;
- premium APIs;
- index and benchmark licensing.

## Issuance policy
Each BTG-created instrument should separately disclose total units, public/strategic/contributor allocations, treasury reserve, transferability, rights, duration, jurisdiction, currency, royalties and derivative participation. Reserve units are moved into the treasury ENTITY rather than left indistinguishable from unsold issuer inventory. Initial reserve allocation is single-use per instrument; policy versioning cannot silently duplicate the reserve or change its size after allocation.

## No token requirement
The BTG treasury does not require an ENTITY coin, founder premine or compulsory protocol levy. Economic value is represented by actual rights positions, contractual receivables, realized service revenue and externally observable market transactions.

## Accounting boundary
ENTITY records are evidence inputs. Indicative reserve marks are not automatically fair-value accounting conclusions, and accrued obligations are not automatically realized revenue. Accounting and tax treatment remain outside protocol inference.

## Reconciliation gate
Before treasury close or release reporting, BTG should run EOPP trade-capture reconciliation and investigate every missing or mismatched in-scope settled EEP trade. A clean reconciliation is evidence of capture completeness, not an accounting audit opinion.
