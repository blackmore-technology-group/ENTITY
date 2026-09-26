# ENTITY Multi-Application Integration Qualification — 2026-09-17

## Scope

Systems exercised:
- ENTITY RC2 production gateway/state
- Boundary's Best / Wild By Nature Soap Studio
- HUNTAR v4.3.0 Android
- SEARCHAR v0.12.0 Android
- HIKEAR v0.1.0 Android

Test objective: verify that application-generated records are captured through ENTITY with signed principal/device/application/installation provenance, user-controller separation, idempotency, fail-closed authorization, non-authoritative application events, and no silent rights/economic mutation.

## Overall status

**NON-HARDWARE ENTITY INTEGRATION: PASS**

**PHYSICAL ARM64 MOBILE RUNTIME LAUNCH: BLOCKED — no Android device is attached to ADB.**

This workstation cannot honestly substitute the installed x86_64 emulator for the production mobile build: all three applications use `arm64-v8a` only and the frozen `NIKI_Mobile_Runtime_0.8.0_android_arm64.aar` contains ARM64 native libraries only.

Therefore the ENTITY/server/integration qualification completed here is not claimed as physical-device qualification.

## Production ENTITY

Production gateway:
- State: `<LOCAL_DRIVE>/BTG_ENTITY_PRODUCTION_STATE`
- Endpoint: `http://127.0.0.1:8787`
- Health: PASS
- Gateway schema: `entity-open-sdk-gateway-v1.1`
- `principal_binding_required=true`
- `bare_entity_ids_accepted=false`

Production ENTITY remained separate from the mobile integration mutations; mobile mutation tests were executed against an encrypted backup restored to an isolated state.

## Boundary's Best

Running executable:
`<LOCAL_DRIVE>/BTG_Qualification_Staging\WildByNatureSoapStudio\setup-full-design-entity-qualified-20260917\payload\WildByNature.SoapStudio.exe`

Observed integration state:
- Outbox: 0
- Sent envelopes: 43
- Response files: 43
- Latest response schema: `entity-open-sdk-asset-result-v1.1`
- Principal binding verified: true
- Controller: Boundary's Best Entity
- Origin installation/device populated
- Ownership inferred: false
- Economic value inferred: false
- Raw content stored: false
- Idempotent replay verified: true

Production identity verification:
- Boundary's Best business Entity: valid
- Soap Studio application Entity: valid
- Soap Studio installation Entity: valid
- Authorized workstation/device Entity: valid


## Mobile source integration changes verified

HUNTAR, SEARCHAR and HIKEAR now each have:
- a dedicated ENTITY SQLite outbox separate from the application's normal backend queue;
- a dedicated ENTITY gateway base URL;
- principal-binding validation before capture;
- automatic lifecycle/event capture;
- automatic mutation capture for application write operations;
- store-and-forward delivery;
- ENTITY response persistence and queue/sent status;
- no acceptance of a bare user Entity ID as a substitute for the signed principal binding.

The event taxonomy was corrected after RC2 properly rejected custom event names. Automatic events now use allowed, non-authoritative namespaces:
- `application.huntar.started` / `data.huntar.mutation`
- `application.searchar.started` / `data.searchar.mutation`
- `application.hikear.started` / `data.hikear.mutation`

ENTITY validation was not weakened to accommodate the applications.

## Final Android build gate

All three corrected sources passed `:app:assembleDebug`.

Final staged APKs:

| App | ABI | SHA-256 |
|---|---|---|
| HUNTAR v4.3.0 | arm64-v8a | `55b10bc925306ece8d8f682945b11363a8a0e7a0574505721cd765662afcb74b` |
| SEARCHAR v0.12.0 | arm64-v8a | `0c8c3312f53eccfca54d79fb7ceed15d283f950d70d287bcdfa490c2232c47e0` |
| HIKEAR v0.1.0 | arm64-v8a | `6e930408a2dfd15cdff9b078bb50adfa10ed539994b7f21e22aa0bdbbcce412a` |

Staged under:
`<LOCAL_DRIVE>/BTG_BUILT_SYSTEMS_2026-09-17_ENTITY_NATIVE\BUILT_APPS`

## Unit/regression task results

- HUNTAR `:app:testDebugUnitTest`: BUILD SUCCESSFUL; module has no JVM unit-test sources.
- SEARCHAR `:app:testDebugUnitTest`: BUILD SUCCESSFUL; module has no JVM unit-test sources.
- HIKEAR `:app:testDebugUnitTest`: 8 tests, 0 failures, 0 errors, 0 skipped.


## Isolated production-clone test

Encrypted production backup was created and restored to:
`<LOCAL_DRIVE>/ENTITY_LIVE_APP_TESTS\MobileApps_RC2_AUTO_CAPTURE\state`

A test device Entity and signed principal/application/device/installation bindings were created only in the restored state.

Application bindings used the real canonical application Entity IDs:
- HUNTAR: `ent2-vkesuqie2o5ldzvon6zro2c5rilor4u6x5lsqrrsw5ypxni73qba`
- SEARCHAR: `ent2-ruiyq6kfvzgjisic7ndo6r4saojc35s5rxqxtd42ddpkexmshs6a`
- HIKEAR: `ent2-427vybtr5qa35uf6qwrda75e2gbwqw7wzjxz2yjtciewfgopzr7a`

Each binding delegated only:
- `INGEST_ASSET`
- `RECORD_EVENT`

The restored gateway on port 8788 reported:
- principal binding required: true
- bare Entity IDs accepted: false

## Positive gateway results

All three applications successfully registered a user-generated DATA asset using the mobile envelope contract.

Canonical assets:
- HUNTAR: `asset1-f15a45bf77fc47858ae50a5f2e4964a3`
- SEARCHAR: `asset1-af7cc2997fa045fa850a4f1137a4fd93`
- HIKEAR: `asset1-0f3943c1839d4076a0557c4697ea2c4c`

For all three:
- controller Entity is the user principal;
- status is ACTIVE;
- classification is PRIVATE;
- capture metadata records `AUTOMATIC_NATIVE_BRIDGE`;
- application Entity is preserved as producer;
- installation Entity is preserved;
- device Entity is preserved;
- principal binding hash is preserved;
- ownership is not inferred;
- economic value is not inferred;
- raw content is not stored in ENTITY.

Each asset has an ACTIVE `DATA_CONTROLLER` claim for the user principal with legal basis `entity_asset_registration`.


## Canonical application events

Verified directly in the restored canonical event ledger:
- HUNTAR: `data.huntar.mutation` — actor is HUNTAR application Entity
- SEARCHAR: `data.searchar.mutation` — actor is SEARCHAR application Entity
- HIKEAR: `data.hikear.mutation` — actor is HIKEAR application Entity

Each event includes the user principal, installation Entity and device Entity as subjects and the corresponding created asset as an object.

ENTITY returned:
- `non_authoritative_application_event=true`
- `economic_state_mutated=false`
- `rights_state_mutated=false`

Asset and event replays returned `idempotent_replay=true` for all three applications.

## Fail-closed / negative tests

PASS:
- Missing principal binding -> HTTP 403
- Application/binding mismatch -> HTTP 403
- Tampered binding signature -> HTTP 403
- Forbidden authority/economic application event -> HTTP 403
- Reusing an idempotency key with a different envelope -> HTTP 400

Control case with a valid binding/envelope -> HTTP 200.

The control result also demonstrated a signed user `DATA_CONTROLLER` claim and preserved the producing HUNTAR application separately.

## Post-mutation state integrity

ENTITY `verify-state` returned `valid=true` for:
- user principal Entity;
- HUNTAR application Entity;
- SEARCHAR application Entity;
- HIKEAR application Entity;
- HUNTAR test installation Entity;
- SEARCHAR test installation Entity;
- HIKEAR test installation Entity.

This verifies state integrity after the successful asset/event/idempotency and negative security tests.

## Remaining hardware gate

ADB currently reports no connected Android devices.

No compatible Android phone is visible through Windows USB/WPD device enumeration.

The existing workstation emulator path is x86_64, while:
- application Gradle configurations restrict native packaging to `arm64-v8a`;
- the frozen NIKI runtime AAR contains only `arm64-v8a` native libraries.

Therefore a physical-device launch cannot be replaced by the x86_64 emulator without building a different NIKI/native runtime, which would no longer be the qualified production artifact tested above.

Required final hardware evidence when an ARM64 Android device is attached:
1. Install each final APK without rebuilding it.
2. Configure/receive its signed ENTITY principal binding.
3. Route the device to the ENTITY gateway.
4. Launch HUNTAR, SEARCHAR and HIKEAR.
5. Generate a normal application write/mutation from each UI/runtime.
6. Confirm the automatic ENTITY outbox sends it without manual bridge calls.
7. Verify the resulting canonical asset/event/controller/provenance in ENTITY.
8. Exercise offline queue -> reconnect -> delivery for each application.
9. Confirm application restart does not duplicate already acknowledged records.
10. Capture device/runtime evidence and then reseal/sign the release.

## Qualification conclusion

ENTITY's non-hardware multi-application integration performed as engineered in this campaign.

The test specifically demonstrated:
- fail-closed signed principal binding enforcement;
- real application Entity identity enforcement;
- device/installation/principal provenance;
- user-controlled mobile data;
- separation of producer from controller;
- canonical asset registration;
- canonical DATA_CONTROLLER rights state;
- idempotency;
- non-authoritative application event boundaries;
- no unauthorized economic or rights mutation;
- encrypted backup/restore isolation;
- post-mutation identity/state integrity;
- working Boundary's Best production integration.

Full mobile runtime qualification remains **PENDING ONLY on the physical ARM64 launch/automatic-capture/offline-reconnect evidence described above**.

