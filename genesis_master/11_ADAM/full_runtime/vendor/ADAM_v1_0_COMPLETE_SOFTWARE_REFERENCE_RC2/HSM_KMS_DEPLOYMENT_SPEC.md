# ADAM v0.43 HSM/KMS Production Key-Custody Specification

## Objective

No production authority private key may be generated, exported, decrypted or held inside the ADAM application or cognition process. Signing is performed by an independently governed custody system.

## Supported production provider contracts

- PKCS#11 HSM using `CKM_EDDSA` or an approved equivalent;
- AWS KMS asymmetric signing key;
- Google Cloud KMS asymmetric signing key;
- Azure Key Vault managed HSM;
- HashiCorp Vault Transit backed by an approved hardware root.

`adam_v43.key_custody.ExternalSignerAdapter` is the narrow provider boundary. It receives only a public descriptor and a signing callback. Private material never enters ADAM.

## Mandatory controls

1. Separate production, recovery and witness key hierarchies.
2. At least 2-of-3 independent authority signatures for constitutional or chemistry changes.
3. Non-exportable keys with provider attestation.
4. Workload identity or mutually authenticated service identity; no static application secrets.
5. Purpose-scoped signing permissions.
6. Jurisdiction and residency controls matching the atom/bond sovereignty policy.
7. Rotation with overlapping public-key verification history.
8. Revocation and emergency-disable procedures.
9. Immutable provider audit logs exported to independent witnesses.
10. Tested backup/recovery that does not expose plaintext private keys.

## Acceptance gates

- provider attestation and key attributes captured;
- private key export operation unavailable;
- unauthorized principal signing rejected;
- wrong-purpose signing rejected;
- quorum continues after loss of one provider;
- two-provider loss prevents constitutional commits;
- rotation preserves old-event verification;
- revoked keys cannot sign new events;
- disaster recovery completed in a separate account or security domain;
- 30-day qualification reports are signed by the production quorum.

## Current build boundary

The included `IsolatedMemorySigner` proves that ADAM can operate without private-key material in the application process and that quorum/rotation logic works. It is software custody and is not represented as an HSM.
