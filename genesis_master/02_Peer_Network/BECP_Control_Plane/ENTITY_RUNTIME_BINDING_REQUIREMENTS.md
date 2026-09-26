# Canonical Runtime Binding — becp_evidence
Authority: `becp_evidence`
Canonical owner: `02_Peer_Network\BECP_Control_Plane`

- BECP records governed outbound commitments, destination, purpose, timestamp, visible response commitment, exposed provider metadata and transport outcome.
- BECP SHALL NOT claim hidden model reasoning, provider routing, undisclosed logs, internal safety processing or other unexposed provider events.
- Unknown provider-internal activity remains `UNKNOWN`.
- Repeated ingestion of the same observable event SHALL be idempotent/deduplicated.
- Evidence origin and assurance level SHALL remain explicit.

## READY Gate
- Tests prove observable-vs-unobservable boundary, tamper detection and duplicate ingestion behavior.
- Imported historical evidence SHALL not be retroactively upgraded to direct observation.
- READY binding pins current `02_Peer_Network\ENTITY_REQUIREMENTS.md` SHA-256.
