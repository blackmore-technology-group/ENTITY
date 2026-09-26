# ADAM v0.41 Architecture — Artificial Living Universe

```text
EXTERNAL APPLICATIONS / HUMANS / MACHINES / SENSORS
                         │
            manifest / JSON-RPC / SQL / SDK
                         ▼
┌────────────────────────────────────────────────────────────┐
│                 UNIVERSAL APPLICATION BRIDGE               │
│ exact event intake │ identity mapping │ temporary views    │
└────────────────────────────┬───────────────────────────────┘
                             ▼
┌────────────────────────────────────────────────────────────┐
│                    COGNITION FABRIC                        │
│ entity perception │ relation perception │ intent planner   │
│ graph reconstruction │ dynamics prediction │ chemistry     │
│                                                            │
│ MODEL PARAMETERS, DATASETS AND METRICS ARE ADAM ATOMS      │
└────────────────────────────┬───────────────────────────────┘
                             │ proposes / simulates
                             ▼
┌────────────────────────────────────────────────────────────┐
│                    GOVERNANCE KERNEL                       │
│ valence │ reactions │ conservation │ authority │ MVCC      │
│ shadow universe │ independent promotion │ proofs           │
└────────────────────────────┬───────────────────────────────┘
                             │ commits
                             ▼
┌────────────────────────────────────────────────────────────┐
│                 AUTHORITATIVE DATA UNIVERSE                │
│ exact graph │ semantic graph │ bonds │ compounds           │
│ model worldlines │ application identities │ reaction history│
└────────────────────────────┬───────────────────────────────┘
                             │ constructs
                             ▼
              JSON / SQL / UI / report / AI context
                    temporary and disposable
```

## Core runtime

`ArtificialUniverseRuntime41` exposes one method surface for:

- bridge registration and upsert;
- temporary application construction;
- cognition interpretation;
- reaction registration, proposal, simulation and commit;
- AQL and read-only SQL execution;
- health and proof inspection.

## Protocol

`ArtificialUniverseHTTP41` exposes JSON-RPC 2.0 at `/rpc`. Any language capable of authenticated HTTP and JSON can bridge to ADAM.

## Model embodiment

A trained model is stored twice without collapsing the graphs:

1. exact model JSON containing parameters and algorithm state;
2. semantic MODEL, DATASET, METRIC, TRAINING_RUN and COGNITION_ORGAN atoms joined by typed bonds.

At inference time the organ reconstructs the model parameters from the exact graph. This makes the universe substrate the model's body and memory rather than an external database attached to the model.

## Governed reaction cycle

```text
OBSERVE → INTERPRET → PROPOSE → SHADOW SIMULATE
        → VALIDATE LAWS / AUTHORITY / VALENCE
        → INDEPENDENT APPROVAL → COMMIT → LEARN → CONSTRUCT
```

A model has no direct commit API. A model proposal approved by the same model identity fails the independent-promotion law.

## Portability

`LivingUniverseCheckpoint41` packages:

- signed compact v0.40 atomic authority;
- constitutional laws;
- reaction registry;
- access policy;
- application bridge registry;
- construction profiles;
- embedded cognition parameters and evidence.

Restore must reproduce the semantic root, exact inventory and embedded model count.
