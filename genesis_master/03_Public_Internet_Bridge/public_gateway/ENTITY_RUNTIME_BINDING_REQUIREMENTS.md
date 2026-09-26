# Canonical Runtime Binding — public_gateway
Authority: `public_gateway`
Canonical owner: `03_Public_Internet_Bridge\public_gateway`

- Public exposure SHALL be separately authorized and SHALL NOT follow automatically from local service readiness.
- Gateway authentication, authorization, rate limits, secure transport and fail-closed policy are mandatory.
- Public events SHALL minimize root identifiers and sensitive metadata.
- External publication SHALL create explicit export evidence and preserve source-asset provenance/rights.
- Irreversible disclosure and broad rights effects SHALL trigger configured approval/warnings.

## READY Gate
- Security qualification covers authentication bypass, replay, scope escalation, disclosure and outage behavior.
- Gateway cannot expose arbitrary vault content or bypass source enrollment/policy.
- READY binding pins current `03_Public_Internet_Bridge\ENTITY_REQUIREMENTS.md` SHA-256.
