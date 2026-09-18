# ENTITY Release-Signing Key Lifecycle and Recovery Runbook

## Purpose

This runbook defines how Blackmore Technology Group manages the cryptographic signing key used for ENTITY Git commits and release tags.

The objectives are:

- preserve release-signing continuity if the primary workstation is lost;
- prevent a signing-key compromise from silently becoming trusted authority;
- keep encrypted recovery material separate from recovery secrets;
- make normal rotation and emergency revocation auditable;
- ensure GitHub branch/tag protections remain aligned with ENTITY's authority model.

This document contains no private key material and no recovery code.

## Current signing identity

Repository: `blackmore-technology-group/ENTITY`

GitHub account: `blackmore-technology-group`

Current signing-key purpose: ENTITY source commits and version/release tags.

Current public-key fingerprint:

`SHA256:55WNqQjYAcuXDGl/T6oPXK8WDXO4M1qbx5jjMCTPmHI`

GitHub signing-key record ID at initial registration: `1185105`.

Reference GitHub-verified commit proving the signing path:

`c900e076c092b6cb3317a980895eff78cf555df0`

The public fingerprint and GitHub record ID are not secret. The private key and recovery code are secrets.

## Required controls

1. The private signing key SHALL NOT be committed to ENTITY or any other Git repository.
2. The private signing key SHALL NOT be copied into documentation, issues, pull requests, CI variables, chat logs, or release assets.
3. Offline backup media SHALL contain only encrypted key recovery material and public recovery instructions.
4. The recovery code/passphrase SHALL NOT be stored on the same offline medium as the encrypted backup.
5. At least two independently recoverable copies SHOULD exist:
   - one encrypted offline copy on healthy removable media;
   - one second encrypted recovery copy in a separately controlled location.
6. GitHub SHALL retain required signed commits on `main` and protected signed version tags.
7. Force pushes and deletion of `main` and protected release tags SHALL remain prohibited.
8. Any key lifecycle event SHALL be documented in an auditable signed commit.

## Current backup format

The initial recovery package uses:

- authenticated encryption: AES-256-GCM;
- password-based KDF: scrypt;
- scrypt parameters: N=131072, r=8, p=1;
- random 128-bit salt;
- random 96-bit GCM nonce;
- recovery code stored separately from the encrypted package;
- encrypted payload checksum and private-key SHA-256 verification.

The recovery envelope contains the OpenSSH private key only after successful authenticated decryption. It also carries the public key, fingerprint, GitHub signing-key record metadata and a known GitHub-verified reference commit for validation.

## Healthy-media requirement

An encrypted backup is not considered durable merely because it decrypts successfully once.

The removable medium used for the authoritative offline backup SHALL report a healthy filesystem/volume state and SHOULD be periodically read-tested.

If Windows, SMART tooling, filesystem tools or the operating system reports warning, repair-needed or degraded state, that medium SHALL NOT be the sole recovery copy.

## Recovery-code handling

The recovery code SHALL be stored separately from encrypted backup media.

Preferred options, in order:

1. a physically written recovery record stored in a secure location;
2. a reputable password manager controlled by BTG;
3. a second sealed physical record in a separate location.

Do not photograph the recovery code for ordinary storage.

Do not store the recovery code in the repository.

Do not place the recovery code in the same directory, archive, USB drive or external disk as the encrypted key backup.

## Recovery drill

A recovery drill SHOULD be performed at least quarterly and after every key rotation.

The drill SHALL:

1. copy the encrypted package to a temporary trusted workstation location;
2. decrypt it using the separately held recovery code;
3. verify authenticated decryption succeeds;
4. verify the recovered private-key SHA-256 against the encrypted package metadata;
5. derive/read the corresponding public key;
6. verify the public fingerprint matches the currently trusted fingerprint;
7. create a local test commit or annotated test tag;
8. verify the test object contains a cryptographic signature;
9. delete the recovered plaintext private key immediately after the drill;
10. record only the date, result and public fingerprint in audit evidence.

A recovery drill SHALL NOT push a test tag to a protected release namespace.

## Normal key rotation

Use normal rotation when the key is not believed compromised but should be replaced due to age, personnel/process change, workstation replacement or cryptographic policy.

### Rotation procedure

1. Generate a new Ed25519 signing key on a trusted workstation.
2. Restrict local filesystem permissions on the private key.
3. Register only the new public signing key with GitHub.
4. Configure Git for SSH signing with the new key.
5. Create a signed transition commit on a non-protected working branch.
6. Verify GitHub reports the transition commit as `Verified`.
7. Open a pull request through the protected `main` workflow.
8. Allow all required CI, CodeQL and dependency-review checks to pass.
9. Merge through the protected workflow.
10. Create a newly encrypted offline backup of the new private key.
11. Verify the encrypted backup through an in-memory or isolated recovery test.
12. Store the new recovery code separately.
13. Update this document's public fingerprint and GitHub key metadata through another signed PR if necessary.
14. Retain the old public key in historical evidence while it remains necessary to verify historical signatures.
15. Remove/revoke the old GitHub signing key only after the new path is proven and recovery material is verified.

Historical signatures remain historical evidence. Rotation does not rewrite prior commits or tags.

## Emergency compromise response

Treat the key as compromised if any of the following occurs:

- the private key is copied to an untrusted system;
- the workstation is stolen or materially compromised;
- malware or credential theft may have accessed the private-key file;
- unauthorized signatures appear;
- the recovery code and encrypted backup are exposed together;
- custody of the private key cannot be established with confidence.

### Immediate actions

1. Stop using the affected private key.
2. Preserve forensic evidence without copying the private key into tickets or chat.
3. Remove/revoke the compromised signing key from the GitHub account.
4. Confirm `main` branch protection, required CI and release-tag protection remain active.
5. Inspect recent commits, pull requests, releases and tags for unauthorized signed objects.
6. Generate a replacement Ed25519 signing key on a trusted system.
7. Register the replacement public key with GitHub.
8. Create and verify a replacement-key test commit outside `main`.
9. Rotate the encrypted offline recovery package and recovery code.
10. Publish a signed security/key-rotation statement using the replacement key once the trusted path is restored.
11. Document the incident timeline, affected fingerprints and remediation without publishing secret material.

## GitHub revocation procedure

For a compromised signing key:

1. Sign in to the authoritative GitHub account.
2. Open account settings for SSH and signing keys.
3. Identify the key by public fingerprint/title.
4. Remove the affected signing key.
5. Verify the key no longer appears in the account's signing-key list.
6. Do not delete or rewrite historical Git objects merely because the key was revoked.
7. Inspect GitHub's verification information on affected objects as part of the incident review.

Revocation stops future trust in the removed account signing key. It does not erase the historical fact that a past signature was created.

## Lost workstation, uncompromised key

If the primary BTG workstation is lost but there is no evidence of compromise:

1. obtain the encrypted offline recovery package;
2. obtain the recovery code from the separate custody location;
3. recover the key only on a trusted replacement workstation;
4. verify the public fingerprint before use;
5. configure Git SSH signing;
6. make a local signed test object;
7. verify GitHub accepts a signed test commit through a working branch;
8. continue normal protected-branch operation.

If custody of the lost workstation cannot be established, use the emergency compromise procedure instead.

## Release-tag procedure

For future ENTITY releases:

1. ensure the release commit has passed all required protected-branch checks;
2. verify the release commit is GitHub `Verified`;
3. create an annotated signed version tag using the configured ENTITY signing key;
4. push the tag only after local signature verification;
5. verify GitHub shows the tag/commit signature as verified;
6. publish the GitHub Release from that protected tag;
7. never force-move or delete an existing public version tag to correct a release;
8. publish a new version/tag for corrections.

The repository ruleset protecting `refs/tags/v*` SHALL remain active.

## Backup media retirement

Before retiring or disposing of media that ever held plaintext signing material:

- securely erase the relevant private-key file where technically meaningful;
- destroy media if secure erasure cannot be trusted;
- confirm at least one independently verified recovery path remains.

Encrypted backup media may be retained for historical disaster recovery only while its recovery secret remains controlled and the cryptography remains acceptable.

## Audit evidence

The following non-secret evidence SHOULD be retained:

- public-key fingerprints;
- GitHub signing-key record IDs;
- signed rotation/revocation commits;
- GitHub verification status;
- backup creation date;
- backup verification date;
- recovery-drill result;
- CI/CodeQL status at key transitions;
- incident/rotation ticket identifier where applicable.

Never record the private key or recovery code in audit evidence.

## Authority principle

Possession of infrastructure or backup media does not confer sovereign authority.

Signing authority is established by the cryptographic key, its controlled registration, the protected repository workflow, and the auditable governance process around its lifecycle.
