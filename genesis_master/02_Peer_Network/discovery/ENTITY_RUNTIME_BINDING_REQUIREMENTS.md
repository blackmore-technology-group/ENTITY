# Canonical Runtime Binding — peer_discovery
Authority: `peer_discovery`
Canonical owner: `02_Peer_Network\discovery`

- Discovery SHALL not imply trust; discovered peers require authentication and policy evaluation.
- Pairwise/context-specific identifiers SHOULD minimize unnecessary correlation.
- Discovery metadata SHALL be minimized and rate/abuse controlled.
- Offline/rejoin behavior SHALL not bypass revocation or trust changes.
- Unknown peers remain untrusted until explicitly validated.

## READY Gate
- Discovery works independently of NIKI and exposes only the declared runtime ABI.
- Tests cover spoofed peer identity, duplicate/replay discovery, stale peer state and rate controls.
- READY binding pins current `02_Peer_Network\ENTITY_REQUIREMENTS.md` SHA-256.
