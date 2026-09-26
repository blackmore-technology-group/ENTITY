# Migration from ADAM v0.42

ADAM v0.43 is a separate branch. The v0.42 distributed living-recreation implementation remains embedded unchanged as the inherited foundation except for the text perception feature contract, which adds deterministic `token_counts` while retaining all previous fields.

New v0.43 modules are under `adam_v43/`. Existing v0.40–v0.42 tests remain part of qualification.

Migration steps:

1. preserve the v0.42 authority and exact-universe directories;
2. install v0.43 alongside v0.42;
3. run `RUN_ADAM_V043_QUALIFICATION.sh` or the PowerShell equivalent;
4. export new semantic and temporal model checkpoints;
5. embed model checkpoints into the atomic universe through the evidence-alignment model vault;
6. configure external HSM/KMS providers before production authority use;
7. build and qualify the Rust authority kernel externally;
8. start the actual 30-day production qualification.
