# Canonical Runtime Binding — relationship_identity
Authority: `relationship_identity`
Canonical owner: `04_Entity_Registry\relationships`

- Root Entity identifiers SHOULD remain private; external relationships use pairwise or purpose-specific identifiers where appropriate.
- Different relationships SHALL NOT require one globally correlatable public identifier.
- Selective disclosure SHALL expose only minimum necessary attributes.
- Verification level remains distinct from identity existence and need not reveal unrelated real-world identity data.
- Relationship mappings and delegated authority SHALL be revocable/auditable.

## READY Gate
- Tests verify pairwise separation, controlled correlation, revocation and minimum disclosure.
- Public/shared records cannot trivially expose root identity through normal relationship operation.
- READY binding pins current `04_Entity_Registry\ENTITY_REQUIREMENTS.md` SHA-256.
