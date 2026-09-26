# Canonical Runtime Binding — peer_transport
Authority: `peer_transport`
Canonical owner: `02_Peer_Network\transport`

- Transport SHALL provide authenticated, encrypted peer communication with replay and duplicate protection.
- Transport success SHALL NOT imply rights, trust, consent or transaction validity.
- Exposed BECP/provider metadata may become evidence; undisclosed internal transport/provider state remains UNKNOWN.
- Network partitions and reconnection SHALL preserve signed-event ordering/reconciliation rules.
- Sensitive identifiers and payload metadata SHALL be minimized.

## READY Gate
- Transport runs independently outside `10_NIKI` and exposes a versioned ABI.
- Tests cover authentication failure, tampering, replay, interruption, rejoin and incompatible protocol versions.
- READY binding pins current `02_Peer_Network\ENTITY_REQUIREMENTS.md` SHA-256.
