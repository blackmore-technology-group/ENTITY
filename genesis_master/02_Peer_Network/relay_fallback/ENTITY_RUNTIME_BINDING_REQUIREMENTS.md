# Canonical Runtime Binding — relay
Authority: `relay`
Canonical owner: `02_Peer_Network\relay_fallback`

- Relay SHALL be a carrier/fallback, not an authority or trust source.
- Payload confidentiality and peer authentication SHALL not depend on relay trust.
- Relay SHALL enforce rate/abuse controls without gaining unrelated Entity permissions.
- Relay metadata SHALL be minimized and retention policy-defined.
- Relay outage SHALL affect only dependent connectivity where feasible.

## READY Gate
- Tests cover relay selection, authenticated peer continuity, tamper/replay attempts, failover and outage.
- READY binding pins current `02_Peer_Network\ENTITY_REQUIREMENTS.md` SHA-256.
