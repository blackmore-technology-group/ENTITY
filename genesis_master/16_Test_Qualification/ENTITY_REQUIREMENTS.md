# ENTITY Test / Qualification Requirements
Source: SERS-ENTITY-003 Complete Master Engineering Design v2.2
Status: Authoritative repository requirement mapping

## Mandatory Test Classes
- Unit tests SHALL cover every security-sensitive state transition with positive and negative cases.
- Property/invariant testing SHALL verify ledger integrity, authorization, balanced accounting, revoked-key rejection, replay safety, provenance preservation, fail-closed policy and read/write separation.
- Adversarial testing SHALL attempt ownership/usage/settlement forgery, ledger forks, replay, payer/payee reversal, vault exfiltration, prompt injection, pairwise identity linkage, fraudulent pool assets, revoked-key use and double-spend.

## End-to-End Qualification
- A fresh Entity A / Entity B scenario SHALL exercise identity, asset enrollment, provenance, rights claims, policy/consent, licence offer/acceptance/activation, controlled access, usage receipt, settlement evidence, accounting/value state, future-use revocation, dispute, ledger verification, backup, restore and independent evidence validation.
- A malicious Entity C SHALL be denied unauthorized consent and usage paths without manual database intervention.
- Corporate-capital Section 170 qualification SHALL remain a separate required E2E scenario and SHALL preserve usage/equity/market-price separation.
- Section 171 SHALL qualify an independently reproducible Transaction Evidence Bundle whose rooted conclusions remain verifiable while the original BTG live state is unavailable and reproduce after sovereign restore.
- Section 172 SHALL qualify that custody, storage and processing do not silently escalate into sovereign, consent, licensing or economic authority, and SHALL prove provider replacement preserves the sovereign Entity root and authority semantics.
- Standards interoperability and destructive sovereignty/recovery SHALL be independently qualified prerequisites of the full E2E gate.
- No manual database edits SHALL be required to pass qualification scenarios.

## Release Evidence
- Full E2E evidence SHALL hash its implementation/tests and the prerequisite qualification artifacts it depends on.
- Missing, failed, unsealed or limited prerequisite evidence SHALL fail the full E2E gate closed.
- Qualification SHALL separately test platform export, identity recovery, evidence boundary, privacy, cryptography, data-loss recovery and performance.
- TRL claims SHALL be evidence-based and MAY differ by subsystem.
- All qualification results SHALL be retained as machine-readable release evidence.
