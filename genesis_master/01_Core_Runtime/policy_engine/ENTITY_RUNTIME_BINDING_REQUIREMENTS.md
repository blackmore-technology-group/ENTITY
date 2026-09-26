# Canonical Runtime Binding — policy_consent
Authority: `policy_consent`
Canonical owner: `01_Core_Runtime\policy_engine`

## Required Capability
- Machine-readable permissions, prohibitions, duties and constraints with ODRL-oriented semantics.
- Consent is specific, purpose-bound, versioned, timestamped and attributable.
- Historical consent retains the policy version active at authorization time.
- Unknown purposes fail closed rather than defaulting to permitted.
- Revocation consequences derive from policy and contract; no false remote-erasure claims.

## READY Gate
- Policy evaluation is authoritative outside `10_NIKI` and exposes a stable ABI.
- Tests cover permission, prohibition, purpose binding, expiry, revocation and policy version changes.
- NIKI receives explanation/projection capability only; it cannot mutate policy directly.
- Migration preserves historical policy/consent meaning.
- READY binding pins current `01_Core_Runtime\ENTITY_REQUIREMENTS.md` SHA-256 and qualification evidence.
