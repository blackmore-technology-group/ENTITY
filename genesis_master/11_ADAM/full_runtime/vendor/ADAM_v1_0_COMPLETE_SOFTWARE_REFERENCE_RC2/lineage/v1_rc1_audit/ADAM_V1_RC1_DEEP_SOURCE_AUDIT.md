# ADAM v1.0-rc1 Deep Source Audit

## Audited package

- Source archive: `ADAM_v1_0.zip`
- Archive SHA-256: `d82113a03ab2f38ec4a8ed73dcd730e0fe3ceb8525bf2af1590b989e2f87d8c9`
- Declared version: `1.0.0-rc1`
- Declared classification: `PRODUCTION_QUALIFICATION_CANDIDATE_NOT_PRODUCTION_CERTIFIED`

## Verified strengths

- The package explicitly refuses to claim production certification while seven external gates remain open.
- The dedicated v0.52-v1.0 test set passed: 20/20.
- The local candidate audit executed 11/11 gates successfully.
- No pickle deserialization, runtime `eval`/`exec`, `NotImplementedError`, or TODO/FIXME/TBD/HACK marker was found in the new operational modules.
- The v1 SHA-256 manifest contains 538 entries and all listed entries matched the extracted archive during an independent verification.
- The package contains concrete custody, network authority, device, training, candidate-freeze, wall-clock and assurance reference implementations rather than documentation alone.

## Blocking findings

### V1-BLOCK-001 — Persistent runtime cannot restart

**Severity:** Critical

`ArtificialLivingUniverseV1Candidate.create()` passes `master_key or os.urandom(32)` to the persistent software custody provider. The CLI does not accept or persist a stable master-key reference. A first run creates an encrypted attestation key, while the second run creates a different random master key and fails with `cryptography.exceptions.InvalidTag`.

**Affected code:**

- `adam_v1/runtime.py`, runtime creation
- `adam_v1/cli.py`, persistent `--state-dir` path

**Reproduced result:**

1. Start `python -m adam_v1.cli --state-dir <dir> --status` — succeeds.
2. Run the identical command again — fails while decrypting `provider-attestation.key`.

**Required correction:**

Use an explicit provider-neutral master-key resolver. Persistent state must require a stable external key reference, Windows DPAPI/credential protection for local reference use, or a real HSM/KMS provider. Never silently generate a replacement key for an existing custody directory.

### V1-BLOCK-002 — Thirty-day qualification state can be edited into a pass

**Severity:** Critical

`RealTimeQualificationController` stores `started_utc`, `required_seconds`, `minimum_witnesses`, invalidations and the public key in unsigned JSON. On restart it reconstructs the monotonic reference from the editable UTC start time. The controller also signs every “daily witness” itself and accepts `witness_id` as unverified text.

**Affected code:** `adam_v57/wall_clock.py`

**Reproduced result:**

- Edit `started_utc` into the past.
- Reduce `required_seconds` and `minimum_witnesses` in the state JSON.
- Reopen with the same controller key.
- Add one controller-signed witness with an arbitrary witness identifier.
- `certification_status()` returns `certified: true`.

**Required correction:**

- Seal the complete controller state with a hardware- or custody-backed qualification key.
- Bind required duration and witness policy to the frozen candidate manifest.
- Never reconstruct elapsed monotonic evidence solely from editable wall-clock state.
- Require independently trusted witness public keys and unique witness signatures.
- Require one valid witness for each actual elapsed day, not merely a count of locally generated records.
- Anchor daily evidence to an external trusted timestamp or independent append-only witness service.

### V1-BLOCK-003 — Assurance promotion accepts an arbitrary self-declared assessor

**Severity:** Critical

`AssuranceCase.attach_assessor_receipt()` verifies a receipt against the public key embedded inside that same receipt. It has no trusted assessor root, approved organization registry, certificate chain, governance approval, or key pin. An arbitrary caller can create a key, label itself independent, mark every external gate passed, sign a PASS receipt and receive `promotable_to_v1: true`.

**Affected code:** `adam_v58/assurance.py`

**Reproduced result:**

- Record all required gates as `passed=True` and `independently_verified=True`.
- Generate an arbitrary Ed25519 key.
- Create a receipt with `assessor_id` different from the operator.
- Sign with that arbitrary key.
- `promotion_status()` returns no blockers and `promotable_to_v1: true`.

**Required correction:**

- Pin assessor trust roots in the frozen production manifest.
- Require a certificate/attestation chain to an approved independent assessor organization.
- Make external gate evidence typed and cryptographically verifiable, not caller-provided booleans.
- Require governance quorum approval for assessor enrollment and gate acceptance.
- Prevent overwrite or downgrade of accepted gate evidence.

### V1-BLOCK-004 — Network quorum certificate proves preparation, not commit

**Severity:** High

The cluster stores node signatures returned during the `prepare` phase as certificate votes. Nodes later commit, but the certificate does not contain commit-phase signatures. An external verifier can prove that a quorum predicted the root, not that a quorum durably committed it. The node server also receives `membership_epoch` but does not validate it, and certificate verification does not validate the epoch against governed membership history.

**Affected code:** `adam_v53/network_authority.py`

**Required correction:**

- Produce separate signed PREPARE and COMMIT votes.
- Build the authoritative certificate from durable COMMIT acknowledgements.
- Bind phase, payload hash, previous root, new root, sequence, membership epoch and deployment identity into every vote.
- Persist and verify governed membership history on each node.
- Reject unknown/stale epochs at the node.
- Define recovery for partial commits without treating an uncertified local append as official authority.

### V1-BLOCK-005 — Candidate and release signatures are self-authenticating

**Severity:** High

`CandidateFreezer.verify()` accepts the public key embedded in the candidate envelope. This proves internal consistency but not that an authorized release authority signed the candidate. The same trust-anchor issue affects promotion evidence.

**Affected code:** `adam_v56/production_candidate.py`

**Required correction:**

Verify candidates against a pinned release/governance public key or HSM attestation included in the parent production manifest. Embedded public keys may provide key material but cannot establish trust by themselves.

### V1-BLOCK-006 — Packaged manifest verifier checks the wrong release

**Severity:** High

`tools/verify_release_manifest.py` is hard-coded to `SHA256SUMS_V0501.txt`. The v1 local PowerShell and shell qualification launchers do not verify `SHA256SUMS_V1.txt` before execution.

The v1 manifest itself independently verified successfully, but the shipped verification workflow does not enforce it.

**Required correction:**

- Make the verifier accept an explicit manifest or select `SHA256SUMS_V1.txt` for v1.
- Reject extra executable/source files unless explicitly allowed.
- Run verification before imports, compilation, tests or demos.
- Verify the outer ZIP hash before extraction and the internal manifest after extraction.

## Important non-blocking release issues

1. `ADAM_v1_0_PRODUCTION.zip` contains the qualification candidate and documents; its name can be mistaken for a production-certified build.
2. `ADAM_V1_FULL_QUALIFICATION_REPORT.md` is duplicated as `ADAM_V1_FULL_QUALIFICATION_REPORT (1).md`.
3. `ADAM_V052_TO_V058_IMPLEMENTATION_MATRIX.md` reports 144 tests while the combined qualification reports 145.
4. The dependency lock pins versions but lacks artifact hashes and platform markers.
5. The CycloneDX SBOM lists direct dependencies but not a complete transitive dependency graph or Rust crate dependency graph.
6. The full packaged regression was not completed again in this audit environment because the inherited isolated suite exceeded the execution window; the dedicated new tests and all local v1 gates did pass.

## Verdict

The submitted archive is a substantive and honestly labeled **ADAM v1.0-rc1 Production Qualification Candidate**. It is not a completed or production-certifiable ADAM v1.0 because the current code permits restart failure, qualification-time manipulation, self-authorized independent assurance, and certificates that do not prove durable quorum commit.

## Required next release

`ADAM v1.0.0-rc2 — Authority Trust and Qualification Integrity Hardening`

Required order:

1. Stable custody and restart-safe key resolution.
2. Trust-anchored candidate/release signatures.
3. Independent signed daily witnesses and sealed elapsed-time state.
4. Trust-rooted assessor enrollment and typed external gate evidence.
5. Durable commit certificates and membership-epoch enforcement.
6. Correct v1 manifest verification and reproducible dependency locks/SBOM.
7. Add adversarial tests for every reproduced bypass.
8. Rerun the full inherited and v1 regression on Windows and Linux.
