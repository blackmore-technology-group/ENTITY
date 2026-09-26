# ADAM v0.50.1 Windows Launcher R2 Fix

This revision supersedes the first final Windows archive.

## Corrected failures

1. PowerShell parsed `"$File:"` as an invalid scoped/drive-style variable reference. The qualification output now uses `"$($File):"`.
2. Standard qualification incorrectly required the optional `coverage` package. Standard mode now requires runtime dependencies plus `pytest`; `coverage` is required only with `-Full`.
3. `-InstallDependencies` previously installed only runtime dependencies. It now installs the package's `[test]` extra, including `pytest` and `coverage`.

## Regression protection

`tests_source_audit/test_windows_portability.py` now verifies the PowerShell-safe subexpression and dependency-mode rules. The complete forced-`spawn` regression is 117/117 with 9/9 integrated logic gates and zero blocking source findings.
