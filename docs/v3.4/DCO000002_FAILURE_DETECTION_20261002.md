# DCO-000002 — Blackmore Real-Time Failure Detection Engine

ENTITY display version: **3.4.3**  
Asset version: **0.1.0**  
Parent: **DCO-000001 / BIRFR-1**

## Asset

DCO-000002 is the first algorithm asset deliberately derived from BIRFR-1.

It detects failure onset from three robot-state signals:

- relative active-joint velocity RMS drop;
- Cartesian force-magnitude jump;
- task-progress delta.

The detector does **not** consume BIRFR-1's generated anomaly-score channel or failure label at runtime.

The algorithm source and calibrated model remain proprietary in controlled BTG storage. Public evidence contains their SHA-256 hashes rather than the protected source/model bytes.

Public asset root:

`60f64ccbed355a1d4a75b0253289487aa2017a513a87cd731f4ee7cc9924cd2e`

Source SHA-256:

`61967179d359ff93085ac3e3f1246fbe3f7afa2cea9dd4b017b768e0bcdb9a97`

Model SHA-256:

`9ecf46feefed093320fbe6db5e1fe80038ed0b0411025620345cea54de8ab2d7`

## Qualification

The initial candidate was rejected because its apparently low timestep-level false-positive rate still produced false alerts in 16.3% of successful held-out episodes.

The qualified candidate changed to onset-relative features and an episode-level validation gate.

Held-out BIRFR-1 result:

- 14,000 failure episodes;
- 6,000 successful episodes;
- failure detection rate: **100%**;
- successful-episode false-alert rate: **0%**;
- early-alert rate: **0%**;
- unknown-failure detection: **100%**;
- cross-embodiment detection: **100%**.

Local pure-Python inference latency:

- median: **4.1 µs**
- p95: **6.3 µs**
- p99: **7.6 µs**

These are controlled synthetic BIRFR-1 results. DCO-000002 has **not** been validated on physical robots and is not presented as a certified safety controller.

BIRFR-1 v0.1 did not seal a physical sampling period, so the detector reports detection delay in ordered timesteps rather than inventing milliseconds.

## Provenance graph

`DCO-000001 / BIRFR-1 → DCO-000002 / Real-Time Failure Detection Engine`

ENTITY records DCO-000002 as a derivative of DCO-000001 rather than an unrelated asset.

## Passport stack

Rights Passport:

- privacy: `CONFIDENTIAL_PROVENANCE`
- SHA-256: `8d83591eae4d221aa9e83c5a4ecfbd297d4cd421df1e209949b6210d4a217de4`

Global Passport SHA-256:

`1a43778b9fc0302584e984ff1041044a11380a6e249adbf6fc75486613018995`

Profiles:

- Global
- Robotics
- AI
- Manufacturing

Economic state remains:

`POTENTIAL / CAD 0`

## BTDU

The Global Passport uses a content-addressed BTDU reference to the qualified BTDU root.

Exact atomization is not claimed.

## Economic family

The reusable `BTG-ADVANCED-ROBOTICS-ALGORITHM-01` template contains seven archetypes:

1. Evaluation
2. Runtime use
3. Enterprise/API
4. Commercial derivative
5. OEM/embedded
6. Field-of-use
7. Regional exclusivity

Ten territory variants expand the seven archetypes to **16 physical EEP instruments**.

Current controlled-prelaunch state:

- 11,868 issued rights units
- 2,030 BTG Treasury reserve units
- 9,838 issuer units
- 0 orders
- 0 trades
- 0 market marks

No live price was invented.

## Shared integration

DCO-000002 binds to the same reusable `ENTITY_ROBOTICS_INTEGRATION` family as DCO-000001.

Exposure remains `NOT_EXPOSED`.

No unique DCO-000002 ROS 2/Open-RMF bridge was created.
