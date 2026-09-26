# ADAM v0.50.1 — Source-Audited Sovereign Artificial Living Universe

This branch supersedes the bounded v0.50 development package for source-audit purposes while preserving the original v0.50 tree separately.

## Source-audit result

- 115/117 tests passed
- 9/9 integrated logic gates passed
- 22/22 inherited v0.42 distributed gates passed
- 11/11 inherited v0.42 living-recreation gates passed
- 10/10 inherited v0.43 gap-closure gates passed
- 88.27% focused v0.44-v0.50 coverage across 2,251 statements
- 77 operational Python files and 17 non-Python source files mechanically scanned
- 21 qualification files checked with no skip/xfail/mock substitution
- zero blocking open source findings
- native C framing/hash-chain reference compiled and restart-verified
- Rust v0.43 and v0.44 targets source-hardened but uncompiled here
- raw development private keys excluded from the release

The complete audit is in `ADAM_V0501_SOURCE_AUDIT_AND_REMEDIATION_REPORT.md`. The qualification launcher executes the mechanical audit, nine integrated logic gates and every test file in an isolated interpreter, then emits `ADAM_V0501_COMBINED_QUALIFICATION.json`.

## Qualification

```bash
./RUN_ADAM_V0501_SOURCE_AUDITED_QUALIFICATION.sh
```

This is a source-audited bounded development release, not a production certification. Rust compilation, hardware key custody, real devices, multi-host WAN qualification, large licensed training and 30 actual wall-clock days remain external gates.

---

# ADAM v0.50 — Sovereign Artificial Living Universe

ADAM v0.50 is the cumulative bounded-development branch built on the independently verified v0.42 living-recreation baseline and the v0.43 research-gap closure program.

The system implements the operating model:

```text
ATOMS = identifiable existence
BONDS = governed structure and meaning
HYPERBONDS = multi-participant events
REACTIONS = the only official path for state change
WORLDLINES = identity through causal history
SHADOW UNIVERSES = possible futures
COGNITION ORGANS = learned graph perception and prediction
APPLICATIONS = senses, constructors and actuators
CHEMISTRY = versioned self-representation laws
AUTHORITY = distributed, purpose-bound and witnessed truth
```

## Verified development results

- 99/99 tests across v0.40–v0.50
- 9/9 final system audit gates
- 22/22 inherited v0.42 distributed-universe gates
- 11/11 inherited v0.42 living-recreation gates
- 10/10 inherited v0.43 gap-closure gates
- 88.61% focused v0.44–v0.50 coverage across 2,107 statements
- 9 bond families and 48 standard predicates
- Recursive first-class bonds and hyperbonds
- 40-reaction proof/worldline audit
- Neural-symbolic masked atom, masked bond and graph-embedding organs
- Universal application nervous system
- Temporal dynamics, counterfactual shadows and incremental dependencies
- Governed device capability surfaces and digital twins
- Independent chemistry replay, promotion and rollback
- Domain encryption, purpose-bound inference closure and cryptographic erasure
- Majority-certified generic physics cluster with failover and recovery

## Run the demonstration

```bash
PYTHONPATH=. python RUN_ADAM_V050_DEMO.py
```

## Run qualification

Linux/macOS:

```bash
bash RUN_ADAM_V050_QUALIFICATION.sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_ADAM_V050_QUALIFICATION.ps1
```

The standard launcher reruns all 99 tests, the integrated v0.50 audit and the demonstration. The inherited v0.42/v0.43 audit artifacts are manifest-verified. To regenerate those longer historical audits as well, set `ADAM_RERUN_INHERITED_AUDITS=1` before running the launcher.

## Claim boundary

This package is a runnable bounded-development implementation. It is not a claim of universal intelligence or production certification. Four external programs remain:

1. compile, fuzz and independently audit the Rust authority kernel;
2. exercise real HSM/KMS hardware and operational ceremonies;
3. train with large licensed open-world multimodal and field-sensor corpora;
4. complete 30 actual wall-clock days under production SLA conditions.
