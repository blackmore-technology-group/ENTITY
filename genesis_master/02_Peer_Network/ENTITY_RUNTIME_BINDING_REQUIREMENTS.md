# Canonical Runtime Bindings — peer network
Authorities: `federation`, `transparency_witness`
Canonical owner: `02_Peer_Network`

## Federation
- Peer trust SHALL require authenticated identity, protocol/schema compatibility and explicit trust policy.
- Signed protocol/version downgrade SHALL fail closed unless an explicitly authorized override exists.
- Required credential type, minimum trust level and trusted issuers MAY gate federation.
- Credential revocation SHALL affect live trust decisions.
- Network partition, reconciliation, replay, duplicate events and finality SHALL be explicit.

## Witness / Transparency
- High-value events SHOULD support Merkle commitments, counterparty signatures, independent witnesses or trusted timestamps.
- A local hash chain alone SHALL NOT be represented as globally authoritative history.
- Public-chain anchoring remains optional.

## READY Gate
- Peer/federation implementations SHALL be outside `10_NIKI` and independently testable.
- READY bindings pin current `02_Peer_Network\ENTITY_REQUIREMENTS.md` SHA-256 and qualification evidence.
