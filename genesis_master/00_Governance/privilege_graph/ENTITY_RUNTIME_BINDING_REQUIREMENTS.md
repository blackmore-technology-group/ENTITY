# Canonical Runtime Binding — privilege_graph
Authority: `privilege_graph`
Canonical owner: `00_Governance\privilege_graph`
Source: SERS-ENTITY-002 §123

- Cross-subsystem authority boundaries SHALL be machine-enforced.
- Unrecognized cross-boundary operations SHALL default deny.
- NIKI SHALL NOT mutate authoritative rights or settlement state.
- ADAM protected export/value transfer SHALL require explicit capabilities.
- BECP responses and untrusted content SHALL NOT create authority.
- BSIE observation SHALL NOT automatically establish ownership.
- Connector scope SHALL NOT expand into unrelated vault scope.

## READY Gate
- Negative authority cases in SERS-ENTITY-002 §123 pass.
- Privilege policy is versioned, hashed and runtime evaluated.
- READY binding pins current `00_Governance\ENTITY_REQUIREMENTS.md` SHA-256.
