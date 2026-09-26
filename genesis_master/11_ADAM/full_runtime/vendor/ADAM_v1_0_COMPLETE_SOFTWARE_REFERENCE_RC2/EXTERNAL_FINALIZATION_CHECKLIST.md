# ADAM v0.43 External Finalization Checklist

## 1. Real multimodal and sensor data

- identify lawful, rights-cleared datasets;
- preserve source, consent, licence and retention metadata as atoms and bonds;
- connect field sensors through the embodiment capability contract;
- label outcomes through governed authority events;
- run drift, OOD, calibration and adversarial evaluations;
- promote models only through the chemistry/model-promotion gate.

## 2. HSM/KMS

- select PKCS#11 HSM or managed KMS providers;
- create three independent authority keys in separate security domains;
- configure 2-of-3 quorum;
- capture hardware/provider attestation;
- run authorization, rotation, revocation and recovery gates;
- bind production qualification reports to the HSM/KMS quorum.

## 3. Rust authority

- install an approved Rust toolchain;
- generate and freeze `Cargo.lock`;
- run format, clippy, tests and release build;
- run protocol conformance and tamper tests;
- fuzz malformed requests and log frames;
- produce reproducible binaries and independent review evidence.

## 4. Thirty-day production qualification

- deploy the Rust authority and HSM/KMS providers;
- install the systemd service or Windows service wrapper;
- start the 30-day controller;
- preserve daily signed reports and host metrics;
- conduct planned failover, restart and recovery exercises;
- after 30 actual days, verify the final certificate independently.
