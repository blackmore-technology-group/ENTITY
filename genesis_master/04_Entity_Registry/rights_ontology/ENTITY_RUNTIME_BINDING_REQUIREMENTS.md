# Canonical Runtime Binding — rights_ontology
Authority: `rights_ontology`
Canonical owner: `04_Entity_Registry\rights_ontology`
Source: SERS-ENTITY-002 §126

- Rights and interests SHALL be modeled as relationships, not a single owner field.
- The ontology SHALL support the stakeholder/right types defined by SERS §§18–20 and versioned extension.
- Verification state SHALL remain separate from dispute/lifecycle state.
- Cardinality, fractional share, scope, territory, duration, legal basis, evidence, delegation, inheritance/succession and supersession SHALL be representable.
- Registration time SHALL NOT automatically resolve ownership/authorship/priority disputes.
- Historical records SHALL retain the ontology/schema version active when they were created.

## READY Gate
- Canonical rights code validates against the ontology vocabulary and preserves backward-compatible aliases without changing old signed meaning.
- Tests cover the complete required vocabulary, state separation and extension/version metadata.
