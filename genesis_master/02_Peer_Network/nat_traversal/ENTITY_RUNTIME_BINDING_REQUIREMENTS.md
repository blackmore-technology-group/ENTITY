# Canonical Runtime Binding — nat_traversal
Authority: `nat_traversal`
Canonical owner: `02_Peer_Network\nat_traversal`

- NAT traversal SHALL be transport infrastructure only and SHALL NOT grant Entity trust or authority.
- Candidate exchange and fallback paths SHALL minimize metadata exposure.
- Authentication/authorization SHALL remain end-to-end and independent of relay/NAT intermediaries.
- Traversal failure SHALL degrade connectivity rather than weaken security policy.

## READY Gate
- Tests cover direct path, failed traversal, relay fallback, peer mismatch and session revocation.
- No traversal mechanism may bypass peer authentication or capability policy.
- READY binding pins current `02_Peer_Network\ENTITY_REQUIREMENTS.md` SHA-256.
