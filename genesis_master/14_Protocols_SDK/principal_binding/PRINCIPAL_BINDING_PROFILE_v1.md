# ENTITY Principal Binding Profile v1

A data-producing application MUST distinguish the sovereign principal, application product, physical/logical device, and installed application instance.

Canonical chain:

`principal Entity -> device Entity -> installation Entity -> application Entity -> governed data/evidence asset`

The human-readable `.entity` alias is not authority. The canonical `ent2-...` Entity ID is authority; the alias-binding SHA provides collision-safe display/disambiguation.

A principal binding is signed by the principal Entity and is revocable. A bare Entity ID MUST NOT establish user authority.

An application installation receives only `INGEST_ASSET` and `RECORD_EVENT` delegation under this profile. It receives no ownership, consent, licensing, payment, settlement, capital, governance, or policy authority.

For user-generated application data, the default asset controller is the bound principal. The producer remains the application Entity. Registration is not legal ownership adjudication.

Every directly captured asset records origin principal, pairwise principal reference, installation Entity, device Entity, producer application Entity, content commitment, and parent lineage.

Derived assets MUST retain parent asset links. Canonical provenance traversal therefore preserves the path back to originating principals even when data passes through other applications, NIKI, ADAM, BSIE, providers, or devices.

Public-facing contexts SHOULD use pairwise principal references when disclosure of the root human/business Entity is not necessary.
