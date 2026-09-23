# ENTITY Protocol 2 — Five-Language Controlled Clean-Room Qualification

Date: 2026-09-23  
Status: **PASS — controlled multi-language clean-room reproducibility**  
External independent implementation status: **PENDING**

## Purpose

This record seals the 2026-09-23 GitHub-hosted qualification of five separately implemented ENTITY Protocol 2 verifier/recovery programs written in Rust, TypeScript, C#, Go and Swift.

The qualification asks whether the published/sealed protocol material is sufficiently deterministic for separately implemented native programs to reach the same verification result without calling or linking the BTG Python reference implementation.

This is a **BTG-controlled clean-room qualification**. It is not represented as proof that an unrelated third party independently authored an implementation without BTG involvement. That stronger external milestone remains pending.

## Clean-room boundary

The common clean-room profile requires each implementation to consume only the sealed conformance kit and prohibits importing, translating, inspecting, calling or linking BTG Python implementation source.

All five repositories contain the same sealed `conformance-kit` Git tree:

`a07a2b1c108b0952b20332d0f72c610146832b50`

Each GitHub Actions workflow verifies every file listed in `conformance-kit/SHA256SUMS.txt` before compiling or executing the implementation. A checksum failure prevents the campaign from running.

## GitHub-hosted execution matrix

| Language | Repository | Qualified commit | GitHub Actions run | Result | Evidence artifact |
| --- | --- | --- | ---: | --- | --- |
| Rust | `blackmore-technology-group/ENTITY-RUST-CLEANROOM` | `ed06520632f6f454d6745b288847589e25c1205b` | `35865352929` | **PASS** | `10752222310` |
| TypeScript | `blackmore-technology-group/ENTITY-TYPESCRIPT-CLEANROOM` | `70f0859ef218eb0406aa473f996912005c135bc2` | `35865374207` | **PASS** | `10751612244` |
| C# | `blackmore-technology-group/ENTITY-CSHARP-CLEANROOM` | `6d2cc46a299d1052d78bd57a95310a09662bd402` | `35865658991` | **PASS** | `10752422841` |
| Go | `blackmore-technology-group/ENTITY-GO-CLEANROOM` | `63280de32601674d4da5cfc5e1d6c6a24634a17b` | `35865403177` | **PASS** | `10752452195` |
| Swift | `blackmore-technology-group/ENTITY-SWIFT-CLEANROOM` | `c271521d5c2824321a1458c9260b7a7b33643354` | `35865450757` | **PASS** | `10752172881` |

The executions occurred on GitHub-hosted infrastructure rather than the BTG development workstation:

- Rust, TypeScript and Go: GitHub-hosted Ubuntu runners.
- C#: GitHub-hosted Windows Server runner / .NET Framework 4.8.
- Swift: GitHub-hosted macOS ARM runner / Swift 6.x.

## Common qualification result

Every implementation reported:

- sealed conformance-kit checksum verification: **PASS**
- vectors passed: **10 / 10**
- sovereign recovery: **PASS**
- recovery signature validation: **PASS**
- recovery artifact hashes: **PASS**
- encrypted state decryption: **PASS**
- restored transaction root equals expected transaction root: **PASS**

Canonical golden transaction root:

`7675954822a2adc2fccf9fb44bc4728f92e93d9741f9b4b669bebd6844f697a1`

Restored recovery root in all five implementations:

`7675954822a2adc2fccf9fb44bc4728f92e93d9741f9b4b669bebd6844f697a1`

## Deterministic cross-language result hashes

All five implementations produced the following identical result SHA-256 values from the same sealed vectors.

| Vector | Expected disposition | Result SHA-256 |
| --- | --- | --- |
| `valid_golden` | accept | `356f5bc434f23b19e048c046684544771bf24d1268a5178fc6f363e131d86505` |
| `invalid_root_tamper` | reject `ROOT_MISMATCH` | `0b91a90afe6822659743fa1e429dd226873b28d9f62b30b5f1a8bc917502cbbe` |
| `invalid_missing_rights` | reject `MISSING_SECTION:rights` | `57cdf62daec7e53c6afd60308bd126b59ca6379cc0ba0543cc3002d3c0464296` |
| `invalid_usage_purpose` | reject `USAGE_PURPOSE_UNAUTHORIZED` | `0eb43ed26960148405a8bae396daeec063e9180c1c8481975c8aa8637cd4376b` |
| `invalid_settlement_direction` | reject `SETTLEMENT_DIRECTION_INVALID` | `e8f54914091b01217e092acbfce679abad82192fe6b1d8f3c8f2cf4ca6869ece` |
| `invalid_commodity_over_settlement` | reject `COMMODITY_EXCEEDS_SETTLEMENT` | `eca68fd672c8e48f76da5ba25d6b53a8a1f48284f3fe511e34fbc2e43d4bf597` |
| `invalid_capital_unbalanced` | reject `CAPITAL_ACCOUNTING_UNBALANCED` | `0ce6de00ddb3591c31bf3d426492b3c1a9ab44051330c39aa8fc015cdb872bb5` |
| `invalid_capital_shares` | reject `CAPITAL_SHARES_UNRECONCILED` | `51caf49fad6ab14f8b8360829e63453a625c882f02637550f62eeab8a1a83ce4` |
| `invalid_ledger_continuity` | reject `LEDGER_PREV_HASH_INVALID` | `c3114d2241c77e34e7a04ff2ead9fc5c8c0759539b4a55f2b8f37414ee9674d1` |
| `invalid_signature` | reject `SIGNATURE_INVALID` | `8089431526b649d1b9f3eb431e82424325b7ba225c050f0785c5befdad9d49d3` |

This agreement means that the separately implemented programs did not merely agree on a boolean PASS/FAIL result. They produced the same canonical verification result state for every campaign vector.

## Evidence artifact digests

GitHub Actions uploaded a three-file evidence package for each successful run containing the campaign report, its SHA-256 and the tested commit identifier.

| Language | GitHub artifact ZIP SHA-256 |
| --- | --- |
| Rust | `b822083a275ec62c8748664688186bb459392d65208834cf6381c381f4b8b5d3` |
| TypeScript | `7a77d989a87fbae24f1841f468b8b24db516361ec0d0d380c8371ff1283c25dc` |
| C# | `38ffe0c2c8dc3ef3965038fcf1dcb3911aa10c960185c243b95d4460286f81f9` |
| Go | `02bbbe8fb63702de3c8869ce9157ad5b0e92890083da3404f93546526d9b1fb0` |
| Swift | `f5ec73c373cac4e2e99213493bd9d2ccc3533145c4c23c4e2448c48b5d7636c9` |

The artifact ZIP digests are container digests and therefore differ across language runs. The protocol-level result hashes above are the values expected to match, and they do.

## C# portability hardening discovered during qualification

The initial C# GitHub-hosted qualification exposed two environment issues before the verifier campaign could execute:

1. the implementation used `System.Web.Script.Serialization.JavaScriptSerializer`, which belongs to .NET Framework rather than `net10.0`; the project was therefore correctly targeted to .NET Framework 4.8 without changing verifier semantics;
2. Windows Git line-ending conversion altered sealed conformance-kit bytes during checkout and was correctly rejected by the SHA-256 integrity gate. `conformance-kit/** -text` was added to `.gitattributes` so Windows checkouts preserve the sealed bytes exactly.

After those portability corrections the sealed-kit hash gate, compile, 10-vector campaign and sovereign recovery all passed on the GitHub Windows runner.

## Qualified conclusion

The 2026-09-23 campaign demonstrates that ENTITY Protocol 2 verification/recovery semantics are reproducible across five native language/runtime implementations under a controlled clean-room process and that GitHub-hosted runners independently execute those implementations to the same canonical protocol outcomes.

The demonstrated claim is:

> **ENTITY Protocol 2 has passed BTG-controlled five-language clean-room reproducibility qualification across Rust, TypeScript, C#, Go and Swift, including sealed-input integrity verification, deterministic valid/invalid vector agreement and sovereign recovery survival.**

The following stronger claim is deliberately **not** made:

> An unrelated third-party implementation has independently passed the full ENTITY external interoperability qualification.

That external milestone requires an unrelated implementer to work from the public/sealed material and complete the published interoperability and sovereign recovery procedure without BTG implementation access.

## Status boundary

- Controlled multi-language clean-room reproducibility: **VERIFIED**
- Five GitHub-hosted native implementation campaigns: **5 / 5 PASS**
- Cross-language canonical result agreement: **VERIFIED**
- Sovereign recovery agreement: **VERIFIED**
- Unrelated third-party implementation: **PENDING**
- Independent external interoperability qualification: **PENDING**
