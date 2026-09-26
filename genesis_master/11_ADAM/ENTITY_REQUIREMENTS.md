# ENTITY / ADAM Integration Requirements
Source: SERS-ENTITY-003 Complete Master Engineering Design v2.2
Status: Authoritative repository requirement mapping

## Authority Model
- ADAM and other agents SHALL operate only under explicit AgentCapability objects.
- Capabilities SHALL define agent, permitted operation, asset scope, counterparty scope, financial limit, time limit, approval requirements, delegation rights and revocation.
- A compromised agent SHALL NOT inherit unlimited authority from the sovereign Entity root.

## Execution
- Every authoritative ADAM action SHALL pass current policy authorization.
- High-impact actions SHALL support mandatory human or organizational approval.
- Approval gates SHOULD cover IP assignment, exclusive licences, high-value contracts, sensitive exports, root/key authority changes, large settlements, irreversible publication and restricted-data AI-training licences.
- Execution SHALL be auditable with actor, authority, object, policy, time and outcome.
- Invalid state transitions and unauthorized execution SHALL fail closed.

## Safety
- Instructions embedded in documents, websites, emails, files or tool output SHALL be treated as untrusted data unless explicitly promoted to authorized instruction.
- Rollback SHALL not rewrite finalized historical evidence; corrective/superseding events SHALL be used where required.

## Full ADAM v1.0 Atomic Information Substrate
- ENTITY SHALL integrate the verified ADAM v1.0 complete bounded software reference as the canonical atomic/evidence state substrate for ENTITY-authorized transitions.
- ADAM SHALL provide deterministic atoms, compounds, typed/recursive bonds, reaction-governed state transitions, exact reconstruction, aligned semantic evidence, history continuity, custody/reference authority services, and bounded distributed-authority mechanisms exposed by the pinned ADAM release.
- ENTITY SHALL remain the root of sovereign identity, delegation, rights, policy, consent and authorization. ADAM SHALL NOT self-grant ENTITY authority.
- Every authoritative ENTITY-to-ADAM transition SHALL carry current authorization evidence and fail closed when that evidence cannot be verified.
- NIKI SHALL receive only bounded ADAM projections and SHALL NOT acquire ADAM mutation authority or ENTITY sovereign authority.
- ADAM historical evidence SHALL be append/supersede oriented; corrections SHALL NOT rewrite finalized historical evidence.
- The canonical integration SHALL pin the verified inner signed ADAM release by cryptographic hash and SHALL distinguish that trust root from non-authoritative packaging wrappers.
- ADAM external certification boundaries SHALL remain explicit and SHALL NOT be promoted to PASS by integration alone.
