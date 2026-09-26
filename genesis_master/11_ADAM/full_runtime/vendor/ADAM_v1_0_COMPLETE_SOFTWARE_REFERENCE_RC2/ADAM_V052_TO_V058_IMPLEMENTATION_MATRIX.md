# ADAM v0.52–v1.0 RC2 Implementation Matrix

| Layer | Implemented software capability | RC2 evidence | External boundary |
|---|---|---|---|
| v0.52 | Provider-neutral custody contracts, encrypted software reference, purpose-separated hierarchy, restart-safe local master material | Custody and restart adversarial tests | Production HSM/KMS/PKCS#11 hardware |
| v0.53 | Process/socket authority, signed prepare and durable commit quorum, epoch-bound governed membership, replay and recovery | Network partition/restart and forged-certificate tests | Physically independent hosts and WAN faults |
| v0.54 | Bounded device capability contracts, simulation stages, expiring commands, safe state and emergency stop | Device safety tests | Certified physical hardware and safety review |
| v0.55 | Governed datasets, held-out groups, bounded specialist organ, OOD abstention and shadow deployment | Training governance tests | Large licensed real-world corpus |
| v0.56 | Trust-anchored candidate freezing, signed qualification cycles and SLO evaluation | Candidate self-authentication attack rejected | External release-key ceremony |
| v0.57 | Signed restart-safe elapsed-time state and independent witness-key registry | State-edit and witness-forgery attacks rejected | Thirty actual elapsed days and external witnesses |
| v0.58 | Pinned assessor registry, typed findings and evidence-bound promotion gates | Self-declared assessor attack rejected | Independent assessor organization |
| v1.0 RC2 | Integrated complete bounded software reference, signed manifest, wheel, launchers and full regression | 148 tests, 12 RC2 gates, source audit, coverage and clean-room checks | External production certification gates |
