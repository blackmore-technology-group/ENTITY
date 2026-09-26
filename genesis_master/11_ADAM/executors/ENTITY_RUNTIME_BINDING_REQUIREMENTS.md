# Canonical Runtime Binding — adam_actions
Authority: `adam_actions`
Canonical owner: `11_ADAM\executors`

- ADAM execution SHALL occur only after current ENTITY policy/capability/approval authorization succeeds.
- Executors SHALL enforce operation, asset, counterparty, financial and time scopes at execution time.
- Instructions contained in documents, websites, emails, files or tool results remain untrusted data unless explicitly authorized.
- Every high-impact execution SHALL produce audit/evidence sufficient to identify actor, authority, object, policy, time and outcome.
- Corrective/rollback actions SHALL NOT rewrite finalized historical evidence.

## READY Gate
- Tests cover unauthorized execution, stale approval, revoked capability, wrong party, prompt injection and duplicate request.
- NIKI cannot directly call an unrestricted side-effect path.
- READY binding pins current `11_ADAM\ENTITY_REQUIREMENTS.md` SHA-256.
