# Canonical Runtime Bindings — Entity Registry
Authorities: `credentials`, `knowledge_capital`, `data_universe`
Canonical owner: `04_Entity_Registry`

## Credentials
- Credential trust SHALL preserve issuer, subject, type, trust level, expiry and revocation state.
- Federation/authorization decisions using credentials SHALL evaluate live revocation and trusted issuer policy.

## Knowledge Capital
- Engineering discussions, requirements, architecture decisions, AI interactions, code lineage, tests and validated datasets MAY be first-class assets.
- Human and AI contributions SHALL both remain represented where known.

## Data Universe
- Data summaries/classifications SHALL not imply ownership or licensing rights.
- AI-generated classification is DERIVED_INFERENCE until accepted/corroborated.
- NIKI projections SHALL be minimum-necessary metadata and SHALL not expose raw vault content by default.

## READY Gate
- Each authority qualifies independently and pins current `04_Entity_Registry\ENTITY_REQUIREMENTS.md` SHA-256.
- No registry binding may convert UNKNOWN or inferred state into verified fact without evidence.
