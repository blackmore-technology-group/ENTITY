# Canonical Runtime Binding — information_projection
Authority: `information_projection`
Canonical owner: `01_Core_Runtime\information_projection`
Source: SERS-ENTITY-002 §124

- All sensitive cross-subsystem information movement SHALL pass an enforceable projection decision.
- Authorization SHALL evaluate subsystem, actor/capability, purpose, classification, rights/consent, target/provider and external-disclosure policy.
- The engine SHALL enforce minimum necessary fields and metadata/content separation.
- Outcomes SHALL include DENY, ALLOW, REDACT, AGGREGATE, PSEUDONYMIZE, DERIVED_ANSWER and REVIEW_REQUIRED.
- Disclosure evidence SHALL record authority/purpose/classification/fields without copying raw sensitive content into the audit record.
- External disclosure uncertainty SHALL fail closed or require review.

## READY Gate
- Negative tests cover metadata-to-content escalation, restricted external disclosure, unknown rights, missing capability and secret-field leakage.
- Positive tests prove minimum projection and redaction.
- READY binding pins current `01_Core_Runtime\ENTITY_REQUIREMENTS.md` SHA-256 and qualification evidence.
