# ENTITY v3.4.1 — Protocol Origin Lineage & Sovereign User Bootstrap

Status: PATCH RELEASE CANDIDATE

ENTITY v3.4.1 corrects a bootstrap-lineage defect discovered after v3.4.0 publication. v3.4.0 introduced Global Passports and continuous provenance, but a fresh deployment locally re-issued the built-in profiles under the deployer's new Entity identity and new passports did not carry a canonical protocol-release origin reference.

v3.4.1 fixes that without changing the five core primitives or rewriting any historical release.

## Added

- canonical signed protocol-origin bundle;
- public signed manifests for Shawn Blackmore, Blackmore Technology Group Limited and ENTITY;
- signed `shawn.blackmore.entity → btg.entity → entity.entity` origin chain;
- signed origin anchors for all nine previously published ENTITY release targets;
- canonical ENTITY-issued v3.4 Global/industry profiles;
- origin-bundle import and verification;
- protocol-origin binding in newly issued Global Passports;
- independent user identity creation during CLI bootstrap;
- CLI origin inspection;
- explicit separation of user asset provenance from protocol origin.
## User sovereignty

A user's own Entity remains the controller of assets that user registers, subject to that asset's actual rights. The protocol-origin record is a separate ancestry reference and does not transfer user authority or ownership to Shawn, BTG or ENTITY.

## Economic continuity

The existing Data Economic Sovereignty, EEP and Originator Participation architecture is unchanged:

- protocol tax remains 0 bps;
- no mandatory cryptocurrency exists;
- provenance alone does not create a royalty;
- originator participation requires explicit, disclosed, signed and effective terms;
- primary allocations, secondary royalties, derivative participation, reserves and service revenue remain available where validly established;
- usage/adoption evidence is not automatically market value or accounting fair value.

## v3.4.0 state migration

Existing v3.4.0 user identities, objects, Rights Passports and signed Global Passports remain immutable. If a v3.4.0 state contains the seven built-in profiles signed by the original deployer, v3.4.1 retains those exact signed profile variants by body hash for historical verification and rebinds only the active canonical profile references to the signed ENTITY protocol identity. New issuance therefore uses canonical ENTITY-issued profiles without invalidating old passports.

## v3.4.1 release-origin attestation

The source tree intentionally contains release-origin anchors for the nine releases that precede v3.4.1. The exact v3.4.1 commit/tree cannot sign itself inside that same commit. After the immutable `v3.4.1` tag is created, BTG generates an ENTITY-signed `ENTITY_CURRENT_RELEASE_ORIGIN.json` sidecar against that exact tag commit and tree. The official release package includes this sidecar. `init` and `ingest` fail closed unless the verified v3.4.1 attestation is present (or supplied with `--release-origin`); verification of historical passports remains available without rewriting them.

## Historical releases

Existing tags and release commits remain immutable. Their signed release-origin anchors refer to those exact historical tag commits and tree hashes. This preserves provenance instead of rewriting history.
