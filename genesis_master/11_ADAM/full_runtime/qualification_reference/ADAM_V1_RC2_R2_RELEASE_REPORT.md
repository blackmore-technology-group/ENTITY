# ADAM v1.0 RC2-R2 Release Report

## Result

ADAM v1.0 RC2-R2 preserves the complete RC2 authority-trust hardening and fixes
the Windows installation-order defect discovered on the target host.

The original RC2 launcher performed an editable installation before verifying
the exact-file manifest. Setuptools correctly generated an `egg-info` directory
inside the extracted source tree, and the manifest correctly rejected the
resulting unmanifested files.

RC2-R2 does not weaken the manifest. It installs pinned third-party dependencies
into an external virtual environment, verifies the signed release tree, installs
the prebuilt signed wheel non-editably, and verifies the tree again afterward.

## Qualification

- 148/148 isolated regression tests passed.
- 12/12 integrated software gates passed.
- Mechanical source audit: zero blocking findings.
- Windows portability test retains the frozen 148-test total and now asserts that
  the v1 installer cannot use editable mode.
- Final installed-package import uses Python isolated mode (`-I`).

## Boundary

This remains a complete bounded software reference. Real HSM/KMS hardware,
physically independent multi-host deployment, certified devices, licensed
open-world training, thirty real elapsed production days, and independent
certification remain external evidence gates.
