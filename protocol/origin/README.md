# ENTITY Protocol Origin Lineage

ENTITY preserves two independent provenance planes:

1. **Asset provenance** — who controls, created, observed, supplied, transformed or derived a particular data/software/physical asset.
2. **Protocol origin** — which ENTITY release/runtime created or verified the passport and the signed origin of that protocol release.

They MUST NOT be collapsed. A user who creates an ENTITY identity and passports their own data remains the controller of that data unless separate rights say otherwise. Protocol origin does not make Shawn Blackmore, Blackmore Technology Group Limited, or ENTITY the owner or controller of user assets.

## Canonical origin chain

`shawn.blackmore.entity` → `btg.entity` → `entity.entity` → ENTITY release → runtime/passport

- Shawn Blackmore: `ent2-6eoiiztjyhmyh2tbr5psmofcduwvjledubhoiqwo6mjfoqkn6ica`
- Blackmore Technology Group Limited: `ent2-kkov66eoh23h3zgr4pe4njsbkayn2kxad6vfyirqvuqrty52clpa`
- ENTITY: `ent2-m3nofxtv3zwldhwuonw3h67hqjh2zambrhj4kaaulncpt4amkcua`
## Canonical bundle

`ENTITY_PROTOCOL_ORIGIN_BUNDLE.json` contains only public verification material:

- the three signed public Entity manifests;
- the signed Shawn → BTG → ENTITY origin record;
- canonical ENTITY-issued v3.4 Global/industry profiles;
- signed release-origin anchors for every published ENTITY release target.

Private signing/recovery keys are never included.

The origin-chain SHA-256 is:

`9d3bdc0ef2e6a27de5368541f6bc014fdec93b2c7af9770d163c804521b9efff`

Historical release tags remain immutable. Release-origin anchors add verifiable lineage without changing those release commits.

## Current release sidecar

The bundle embedded in the v3.4.1 source tree anchors the nine releases that existed before v3.4.1. An exact release cannot embed a signature over its own final commit hash without creating a self-reference. Therefore the immutable `v3.4.1` tag is followed by an ENTITY-signed `ENTITY_CURRENT_RELEASE_ORIGIN.json` sidecar that names the exact tag commit and tree. The official release package ships that sidecar at the package root. A source checkout may provide it explicitly with `--release-origin`. New v3.4.1 `init` and `ingest` operations fail closed without a valid v3.4.1 sidecar; old passports remain readable/verifiable under their original release semantics.

## v3.4.0 profile migration

A v3.4.0 installation may already contain the seven built-in profile refs signed by its deployer. v3.4.1 preserves those signed variants by their original body hashes so historical Global Passports continue to verify, while making the canonical ENTITY-signed variants active for all new issuance. The migration does not rewrite the user's Entity, objects, Rights Passports, historical Global Passports, or economic records.

## Economic boundary

Protocol origin is **not** an automatic royalty, tax, fee or market-value claim.

ENTITY's Data Economic Sovereignty doctrine and Originator Participation Profile allow an originator to retain economic participation only when the relevant right, reserve, royalty, derivative participation or service term is explicitly established, disclosed, signed and effective for the economic event.

Accordingly:

- `automatic_protocol_royalty_bps = 0`;
- protocol origin does not create legal title;
- protocol origin does not determine accounting or market fair value;
- adoption/usage may become attributable evidence, but it is not automatically monetary value;
- a disconnected installation cannot silently report usage to BTG or Shawn.

This separation preserves user sovereignty while retaining verifiable protocol ancestry and a lawful/evidence-bound path for explicitly established economic participation.
