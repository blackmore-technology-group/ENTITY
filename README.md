# ENTITY

**Provider-independent sovereign digital authority infrastructure.**

ENTITY is Blackmore Technology Group's open-source protocol and reference implementation for persistent Entity identity, delegated authorization, provenance, rights claims, verification, portable state, recovery, and trusted application interoperability.

> Infrastructure possession does not become sovereign authority.

## Independent implementers wanted

ENTITY Protocol 1.0 is **FROZEN_FOR_EXTERNAL_CONFORMANCE**, and BTG is actively seeking an unrelated implementation built from the public protocol rather than from the BTG reference runtime.

Rust, Go, C#, TypeScript, Java/Kotlin and Swift implementations are especially useful. The authoritative sealed kit provides the protocol, schemas, profiles, trust material, valid/invalid vectors, black-box runner and live-interoperability procedure.

- **[Join the independent implementation discussion](https://github.com/blackmore-technology-group/ENTITY/discussions/9)**
- **[Take the clean-room conformance challenge](https://github.com/blackmore-technology-group/ENTITY-Protocol-1.0-Conformance-Kit/issues/2)**
- **[Open the sealed ENTITY Protocol 1.0 Conformance Kit](https://github.com/blackmore-technology-group/ENTITY-Protocol-1.0-Conformance-Kit)**

Independent external interoperability is still **PENDING**. These public challenges exist to test that milestone rather than assume it.

## Download ENTITY for Windows

**ENTITY 1.0.0-rc2 for Windows x64 is publicly available now.**

> **[Download ENTITY 1.0.0-rc2 for Windows x64](https://github.com/blackmore-technology-group/ENTITY/releases/download/v1.0.0-rc2/ENTITY_1.0.0-rc2_WINDOWS_x64_SIGNED.zip)**

Release page: **[ENTITY 1.0.0-rc2 — First Public Release Candidate](https://github.com/blackmore-technology-group/ENTITY/releases/tag/v1.0.0-rc2)**

| Windows release item | Value |
| --- | --- |
| Product version | **1.0.0-rc2** |
| Platform | **Windows x64** |
| Archive | `ENTITY_1.0.0-rc2_WINDOWS_x64_SIGNED.zip` |
| SHA-256 | `aa02846cfbfe4871aa093815cbb269b82ac9551b513c9b872c84584576b42aa4` |
| Distribution signature | **ENTITY Ed25519 signed manifest — verified** |
| Microsoft Authenticode | **Not currently signed** |
| Independent external interoperability | **PENDING** |

The archive contains the Windows GUI and CLI, the sanitized canonical runtime required by the launchers, build provenance, public signer material, SHA-256 verification material, and the signed ENTITY release manifest.

The Windows product release and the protocol conformance kit are deliberately separate:

- **ENTITY** — the actual open-source reference implementation and downloadable Windows product.
- **[ENTITY Protocol 1.0 Conformance Kit](https://github.com/blackmore-technology-group/ENTITY-Protocol-1.0-Conformance-Kit)** — the authoritative sealed clean-room test target for independent implementations.

The repository has subsequently received RC2.1/RC2.2 source and public-packaging corrections. The currently published Windows executable build identifies itself as **1.0.0-rc2**, so it remains attached to the matching immutable `v1.0.0-rc2` release rather than being relabeled as a different binary version.

ENTITY is designed so that a person, organization, application, or other Entity can preserve cryptographic identity and governed authority across devices, hosts, providers, and infrastructure changes without making a storage provider, cloud host, registrar, resolver, application vendor, or Blackmore Technology Group the sovereign authority merely because it operates infrastructure.

## Release status

| Component | Status |
| --- | --- |
| Public source/reference repository | **1.0.0-rc2.2** |
| Windows x64 product build | **1.0.0-rc2** — [download](https://github.com/blackmore-technology-group/ENTITY/releases/tag/v1.0.0-rc2) |
| ENTITY Protocol | **1.0 — FROZEN_FOR_EXTERNAL_CONFORMANCE** |
| Master requirements | **SERS-ENTITY-003 v2.2 — 172 normative sections** |
| Sovereign Domain profile | **SERS-ENTITY-DOMAIN-001 v1.0** |
| Internal qualification | Evidence-backed RC2 qualification completed for the published reference implementation scope |
| Independent external interoperability | **PENDING** |

The protocol freeze stabilizes semantics for external conformance work. It is **not** a claim that unrelated third-party implementations have already passed interoperability qualification.

## Core invariants

ENTITY separates concepts that conventional platforms often collapse:

- **Identity is not an account.**
- **Registration is not ownership.**
- **Provenance is not proof of legal rights or truth.**
- **Possession, hosting, routing, or storage do not create sovereign authority.**
- **Applications and agents act only through explicit, scoped, revocable authority.**
- **Usage does not become realized economic value without the required evidence.**
- **Historical signed semantics are superseded, not silently rewritten.**
- **An Entity identity survives replacement of a device, host, provider, or BTG infrastructure.**

## Repository layout

```text
ENTITY/
├── src/
│   ├── 01_Core_Runtime/
│   ├── 04_Entity_Registry/
│   ├── 08_Data_Vaults/
│   ├── 15_Operations/
│   └── 22_Sovereign_Domain/
├── sdk/
│   ├── open_entity_sdk/
│   ├── open_entity_sdk_v1_1/
│   ├── principal_binding/
│   ├── simple_sdk/
│   ├── android_sdk/
│   ├── apple_sdk/
│   ├── web_sdk/
│   └── windows_sdk/
├── protocol/
├── docs/
│   ├── requirements/
│   ├── architecture/
│   └── qualification/
├── examples/
└── tests/
```

The repository intentionally excludes production databases, private keys, machine-specific principal bindings, recovery secrets, operational backups, BTG production state, generated installers, and qualification environments.

## Quick start

Python 3.11+ is recommended for the reference implementation.

```powershell
git clone https://github.com/blackmore-technology-group/ENTITY.git
cd ENTITY
python -m pip install -r requirements.txt
python -m compileall -q src sdk protocol
python -m unittest discover -s tests -v
```

A minimal developer facade is provided at:

```text
sdk/simple_sdk/canonical_simple_entity_sdk.py
```

The Open SDK v1.1 separates the **producer application** from the **asset controller** and requires an explicit principal/device/application binding before canonical ingestion.

The Open SDK does not require raw content bytes. Applications can submit cryptographic hashes and bounded metadata while retaining source data under the controller's own custody.

## Open SDK event boundary

Generic application events are intentionally non-authoritative. Allowed event namespaces include:

```text
application.*
data.*
model.*
knowledge.*
software.*
evidence.*
```

Generic events cannot be used to bypass canonical authority, consent, rights verification, licensing, settlement, payment, capital, or Digital Commodity subsystems.

## Sovereign Domain

ENTITY Sovereign Domain is designed around a stronger requirement than ordinary DNS or hosting:

> No Entity shall be required to rent continued digital existence from an infrastructure provider.

An Entity domain binds to the cryptographic Entity root rather than a specific DNS account, IP address, device, cloud host, or BTG account. The current profile is defined by `SERS-ENTITY-DOMAIN-001 v1.0`.

Independent external sovereign-domain qualification remains pending.

## Security boundary

**Never commit operational sovereignty state to this repository.**

Do not commit:

- private signing or recovery keys;
- principal/device/application binding instances;
- `.entitybackup` files;
- SQLite/runtime databases;
- live credentials, tokens, cookies, or API secrets;
- production state directories;
- unredacted user or business data.

See [SECURITY.md](SECURITY.md).

## Requirements and protocol governance

The controlling engineering baseline is:

- [SERS-ENTITY-003 v2.2](docs/requirements/SERS-ENTITY-003_v2.2_COMPLETE_MASTER_ENGINEERING_DESIGN.md)
- [SERS-ENTITY-DOMAIN-001 v1.0](docs/requirements/SERS-ENTITY-DOMAIN-001_v1.0.md)
- [ENTITY Protocol 1.0 Freeze](protocol/ENTITY_PROTOCOL_1_0_FREEZE.json)
- [Protocol Governance](protocol/ENTITY_PROTOCOL_GOVERNANCE_v1.md)
- [Sovereign Authority Doctrine](docs/architecture/ADR-0004-SOVEREIGN-AUTHORITY-DOCTRINE.md)

## License

ENTITY is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE).

Blackmore Technology Group may steward specifications and publish new versions, but a conforming published protocol version is not intended to require BTG hosting, DNS, a BTG resolver, or a paid BTG service.

## Project

**Blackmore Technology Group Limited**
Repository: `blackmore-technology-group/ENTITY`
