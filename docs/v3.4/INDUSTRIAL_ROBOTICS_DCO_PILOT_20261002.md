# Industrial Robotics DCO Product Family — Strategic Controlled Prelaunch

Date: 2026-10-02  
ENTITY display version: **3.4.3**  
DCO: `DCO-BTG-ROBOTICS-DATASET-001`  
Commercial profile: **Strategic DCO / 12 archetypes**

## Status

The Industrial Robotics DCO has been expanded from the initial seven-product economic structure to the complete Blackmore Strategic DCO framework.

The underlying asset remains the same governed DCO. The expansion adds commercial rights instruments; it does not create additional DCOs.

The controlled pilot dataset still contains **10,000 deterministic synthetic robotics telemetry records** and still makes no claim of established commercial value.

Dataset SHA-256:

`ee246c4af5380daf178d8a85112ba5ae22b6379345e2ecfa1307fb6dcf881563`

Dataset-manifest SHA-256:

`4b3eb8edaef0aa165481d257b2525caf1ee18dcb6e45bcc7d9a2bb996cd6e2da`

## Twelve strategic commercial archetypes

1. Evaluation
2. Inference
3. Training
4. Compute-to-data
5. Enterprise/API
6. Commercial derivative
7. OEM/embedded
8. Field-of-use
9. Redistribution
10. Synthetic/derived data
11. Regional exclusivity
12. Contributor participation

These are commercial product archetypes, not new protocol instrument classes. They are expressed through the six existing ENTITY v3.4.3 EEP classes and their rights/terms.

Regional exclusivity is one archetype with ten territory-specific physical EEP instruments. Therefore the twelve archetypes currently map to **21 physical instruments**.

## Product family

| Archetype / product | Symbol | Supply | BTG Treasury reserve | Scarcity |
| --- | --- | ---: | ---: | --- |
| Evaluation | `BTG-RBT-EVL` | 1,000 | 0 | Open capacity |
| Inference | `BTG-RBT-INF` | 10,000 | 2,000 | Controlled capacity |
| Training | `BTG-RBT-TRN` | 1,000 | 250 | Fixed cap |
| Compute-to-data | `BTG-RBT-CTD` | 5,000 | 0 | Controlled capacity |
| Enterprise/API | `BTG-RBT-ENT` | 250 | 0 | Controlled capacity |
| Commercial derivative | `BTG-RBT-DER` | 100 | 30 | Fixed cap |
| OEM/embedded | `BTG-RBT-OEM` | 500 | 0 | Controlled capacity |
| Field-of-use | `BTG-RBT-FOU` | 8 | 0 | Fixed cap |
| Redistribution | `BTG-RBT-RED` | 50 | 0 | Fixed cap |
| Synthetic/derived data | `BTG-RBT-SYN` | 500 | 0 | Fixed cap |
| Regional exclusivity | 10 territory symbols | 10 × 1 | 0 | Unique |
| Contributor participation | `BTG-RBT-CON` | 10,000 | 0 | Fixed cap |

Aggregate issued rights supply: **28,418 units**.

Actual BTG Treasury reserve: **2,280 units**.

Issuer inventory after reserve allocation: **26,138 units**.

The aggregate rights-unit count spans heterogeneous commercial units and should not be interpreted as one homogeneous security, currency or valuation measure.

## Field-of-use model

The Field-of-use archetype has eight fixed slots:

- warehouse automation;
- manufacturing;
- mining robotics;
- agricultural robotics;
- construction robotics;
- logistics;
- inspection/maintenance;
- research.

A field must be bound at contract activation. The instrument terms require one active binding per field.

## OEM / embedded model

The initial OEM series contains **500 units**, with one unit defined as capacity for **100 authorized deployed robots/devices**. This creates an initial metered deployment capacity of **50,000 devices** without transferring source-data redistribution rights.

## Contributor participation model

The Contributor Participation series contains **10,000 fixed units**, with one unit defined as one basis point of contributor-pool weighting.

Issuance does not itself create cash entitlement. Allocation requires accepted provenance evidence, and an explicit revenue-pool rule must exist before distribution.

## Version rights

The Enterprise/API template carries version-access options for:

- current version;
- continuous updates;
- LTS option.

The DCO Master Economic Record also supports version relationships rather than treating every update as an unrelated new DCO.

## Master Economic Record

The installed runtime now has one application-layer Master Economic Record for this DCO covering identity, version, economic profile, instrument/archetype summary, supply, treasury position, market state, economic state, version policy and factory classification.

Master-record SHA-256:

`f68352450bca465cb15642e271bdb857c22a586a35406b3538e64a3c6c30aeac`

## Market state remains deliberately clean

The strategic expansion created no artificial price event:

- **0 orders**;
- **0 trades**;
- **0 market marks**.

The previously published prices remain illustrative reference terms for the original products. No prices were invented for the newly added products.

The wallet therefore keeps all robotics positions unpriced until qualifying market activity exists.

## Integrity

Post-expansion SQLite `quick_check` returned `ok` for:

- ENTITY Exchange Protocol state;
- Economic Participation state;
- ENTITY Wallet state.

The Universal Transaction Fabric was not rewritten by the strategic expansion; its initial DCO registration qualification had already returned `ok`.

## Scale path

This DCO is the reference instance for the reusable `BTG-STRATEGIC-AI-ROBOTICS-01` DCO Factory template.

The factory is designed so future DCOs inherit standardized archetypes, scarcity rules, duplicate/version checks and a Master Economic Record instead of requiring manual contract design for every asset.

ENTITY remains **v3.4.3**.
