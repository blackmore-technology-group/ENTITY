# ENTITY DataChip EXECUTE-rights Stage 7 — Windows integration evidence

**Observation date:** 2026-10-13  
**Machine:** BTG authorized Windows 11 workstation (Desktop Commander online and responsive)  
**Workspace:** `D:\Blackmore\Fabric_Integration_20261013_Stage7` (isolated copy; production installation and databases were not written)

## Exact source under test

- `sdk/datachip/execution_rights.py`: new experimental execution-rights ABI on the PR branch
- `sdk/datachip/execution_host.py`: new bounded in-memory host
- `tests/test_entity_datachip_execute_authority.py`: actual ENTITY `RightsPassportRegistry`, synthetic controller/signing fixture, Ed25519 issuer/revoker and genuine EDCF `pack_formula_bytes` generation
- `sdk/datachip/authority_bridge.py`, `rights.py`, `processor.py`, `formula_chip.py`, `src/36_Adoption_Layer/rights_passport.py`, `src/40_BTDU/formula_kernel.py`, `src/40_BTDU/storage_kernel.py`: copied as source from current ENTITY main to isolate the system tests, not modified
- Existing tests `test_entity_datachip_authority_bridge.py` and `test_entity_datachip_formula_rights.py` copied unchanged

## BTG Windows console qualification

```powershell
Set-Location D:\Blackmore\Fabric_Integration_20261013_Stage7
python -B -m unittest discover -s tests -p test_entity_datachip_execute_authority.py -q
# Ran 28 tests in 1.586s — OK
python -B -m unittest discover -s tests -p test_entity_datachip_authority_bridge.py -q
# Ran 10 tests in 0.545s — OK
python -B -m unittest discover -s tests -p test_entity_datachip_formula_rights.py -q
# Ran 18 tests in 0.712s — OK
```

**Total: 56/56 independently categorized test cases PASS on Windows.** These are three suites, not a claim that all tests in the main ENTITY repository passed.

The formula-rights suite initially could not import `src/40_BTDU/formula_kernel.py` and subsequently `storage_kernel.py` because these files were omitted from the isolated source copy. After copying those **unchanged** source dependencies from ENTITY main, all 18 tests passed. There was no product-code fix to work around that missing-fixture error.

### Positive behaviors exercised

1. Actual ENTITY signed Rights Passport and live read-only SQLite status, plus authenticated controller decision, issue an **EXECUTE-only** signed grant through an external signing callback.
2. Independently signed, time-bounded revocation snapshot has issuer coverage and explicit grant/passport/issuer denial.
3. Genuine formula SDK reconstructs an actual EDCF v0.2 test chip **in memory**; an allowlisted deterministic operation returns only an output SHA-256, not reconstructed payload bytes.
4. Export-only grants, tampering, wrong chip/assembly, wrong device, rejected license, stale sequence, conditional rights, PROHIBIT, supersession, ambiguous active versions and unsupported operations fail closed.
5. Unmodified existing EXPORT authority bridge and EDCF rights tests continue to pass.

## Release gates and claims

**NOT PRODUCTION CONNECTED.** Test signer/controller identity was generated synthetically. The test registry is a real implementation running against a temporary SQLite database, **not** the live production ENTITY Rights Passport registry. There is no evidence of production KMS/HSM keys, approved key custody, trusted revocation service, externally attested device, real licensing entitlement, protected monotonic sequence or native iPhone deployment in these tests.

The committed cross-platform workflow is a separate qualification requirement; do not claim it passed until the platform reports successful jobs. A signed grant alone does not give legal title, economic settlement, data export permission, or device access. The capability remains Draft PR-only and **not deployed**.
