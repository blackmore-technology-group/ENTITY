# ENTITY Global Passport SDK

ENTITY v3.4 exposes one Global Passport across composable jurisdiction, industry and technical profiles. The SDK wraps existing sovereign primitives, v3.2 Rights Passports, v3.3 Evidence Objects, v3.4 profiles, continuous provenance and executable industry packages.

It does **not** create authority, determine legal ownership, assert regulatory compliance, establish objective truth, or make external standards subordinate to ENTITY.

Built-in profile aliases are `global`, `healthcare`, `finance`, `manufacturing`, `ai`, `robotics`, and public/unclassified `defence` / `defense`.

## Developer model

The deployer configures organization-specific facts; the deployer does not redesign ENTITY semantics.

```python
sdk.package_plan("healthcare", config, "clinical_dataset")
sdk.map_external("healthcare", "HL7-FHIR", fhir_resource)
sdk.ingest_package_file(path, controller_entity_id, "healthcare", config, "clinical_dataset")
sdk.verify_passport(global_passport_id)
```

The package layer pre-engineers object types, rights defaults, evidence expectations, privacy defaults, external-standard mappings and profile composition. Continuous ingestion registers content by SHA-256, creates the ENTITY object, Evidence Object, Rights Passport and Global Passport, records provenance, and writes a zero-value economic baseline unless supported evidence establishes a different economic state.

External-standard mappings are explicitly versioned correspondences only. They do not redefine FHIR, DICOM, ISO 20022, FIX, LEI, OPC UA, AAS, SPDX, CycloneDX, NIST AI RMF, ROS 2, Open-RMF or any other external standard.

The command-line deployment facade is `tools/entity_v3_4_cli.py` with `init`, `packages`, `plan`, `map`, `ingest` and `verify` operations.
