# ENTITY Open Developer SDK v1

Purpose: allow any application to become an ENTITY-native producer without making BTG, DNS, a cloud host, or a registrar sovereign authority.

Identity model:
- `display_alias`: human-readable name such as `huntar.entity`; aliases may collide.
- `entity_address`: canonical sovereign `ent2-...` Entity root; this is the authoritative address.
- `entity_address_sha256`: hash of the canonical address for compact verification/display.
- `alias_binding_sha256`: hash of namespace + alias + Entity root; this uniquely disambiguates duplicate aliases.
- `collision_safe_display`: alias plus short binding fingerprint for UI use.

Data model:
Applications submit content hashes and metadata, not raw data bytes. ENTITY records software, data, model, knowledge and evidence assets with origin Entity, provenance, source/data-subject references, optional explicit rights claims and derivation lineage.

Security boundaries:
- authorization defaults to deny;
- registration never proves ownership;
- provenance never proves rights or truth;
- duplicate aliases never replace cryptographic Entity-root verification;
- app events cannot bypass consent, rights verification, licensing, settlement, Digital Commodity, payment, authority or capital subsystems;
- storage/provider/device possession never becomes sovereign authority.

The JSON envelope is language/platform neutral. Python here is the reference implementation; Android, Apple, Windows, Web, Linux and other SDKs should reproduce the same envelopes and verification rules.
