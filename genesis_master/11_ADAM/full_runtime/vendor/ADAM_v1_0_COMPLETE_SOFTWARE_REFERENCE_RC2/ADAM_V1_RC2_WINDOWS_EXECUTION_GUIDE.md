# ADAM v1.0 RC2 Windows Execution Guide

Place these files in one directory:

- `ADAM_v1_0_COMPLETE_SOFTWARE_REFERENCE_RC2.zip`
- `ADAM_v1_0_COMPLETE_SOFTWARE_REFERENCE_RC2.zip.sha256`
- `START_ADAM_V1_RC2_WINDOWS.ps1`

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\START_ADAM_V1_RC2_WINDOWS.ps1 -InstallDependencies -Full
```

For the inherited strict Rust gate:

```powershell
powershell -ExecutionPolicy Bypass -File .\START_ADAM_V1_RC2_WINDOWS.ps1 -Full -RequireRust
```

The standard software gate verifies the outer ZIP, signed internal manifest, 148 regression tests, 12 rc2 integrated gates, source audit, wheel imports and focused v1 coverage.
