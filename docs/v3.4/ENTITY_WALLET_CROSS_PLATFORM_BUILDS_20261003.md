# ENTITY Wallet cross-platform builds — 2026-10-03

**Runtime family:** ENTITY v3.4.3
**Wallet architecture:** ENTITY Data Economy Terminal
**Canonical desktop implementation:** PySide6 / Qt + canonical ENTITY runtime modules
**Final desktop qualification before cross-platform build publication:** 91/91 PASS

## Build surfaces

The repository publishes four build artifacts from the `ENTITY Wallet Cross-Platform Builds` GitHub Actions workflow:

| Artifact | Build environment | Scope |
| --- | --- | --- |
| `ENTITY-Wallet-Windows` | `windows-latest` | Full canonical desktop wallet |
| `ENTITY-Wallet-Linux` | `ubuntu-latest` | Full canonical desktop wallet |
| `ENTITY-Wallet-macOS` | `macos-latest` | Full canonical desktop wallet |
| `ENTITY-Wallet-iOS-Simulator` | `macos-latest` + Xcode | Native iOS portable-snapshot inspection client |

Windows, Linux and macOS execute the same Python/PySide6 wallet source and package the same canonical runtime modules.

## iOS boundary

The current canonical wallet implementation is a Python/PySide6 desktop application. Its PyInstaller deployment path targets desktop operating systems and is not treated as an iOS authority runtime.

The iOS target is therefore deliberately implemented as a native SwiftUI **portable wallet inspection client**. It can import a portable JSON wallet snapshot and display:

- wallet lineage;
- issuer namespace and market-registry version when present;
- Digital Commodity Object holdings;
- asset codes and immutable object identifiers;
- explicit domain lineage;
- Rights-Passport `ALLOW` actions present in the imported snapshot;
- issued economic instruments, market identifiers/tickers, rights classes and instrument actions;
- the explicit `NO TICKER` condition when an asset has no economic instrument.

The iOS client does **not** silently create a human identity from device information and does not locally invent authority.

Canonical write operations remain ENTITY runtime operations, including:

- sovereign identity creation/adoption;
- device-bound signing and authentication;
- DCO registration;
- Rights Passport / Global Passport issuance;
- economic instrument issuance;
- listings and signed market orders;
- settlement/economic-state mutation.

This keeps the mobile build useful without falsely representing an unqualified native port as equivalent to the canonical desktop authority engine.

## Rights-driven issuance retained across builds

The current wallet rule is:

`DCO Rights Passport = maximum authorized actions`

`Economic Instrument = selected subset of those authorized actions`

The desktop wallet presents only current Rights-Passport `ALLOW` actions as directly selectable economic rights. The canonical market registry independently rejects any instrument whose requested actions exceed the Rights Passport.

The iOS client reflects imported Rights-Passport actions but cannot expand them.

## Domain state

The production wallet qualification used for the final Windows rebuild resolved all 12 current wallet assets to explicit domains:

- 10 × **Software Engineering**;
- 2 × **Robotics**;
- 0 × missing domain.

The Software Engineering profile is distributed as `entity-profile:software-engineering@1.0` with a pre-signed canonical profile record under `protocol/profiles`.

## First-run identity model

A clean desktop installation follows:

`Install → create/adopt ENTITY identity → claim public .entity alias → optional organization → bind Device ENTITY → authenticate → open wallet`

Device metadata is not allowed to silently become a human or organization identity. Public names are aliases; immutable Entity IDs and signatures remain authoritative.

## Qualification and packaging

The final focused wallet/economy/lineage/onboarding/global-passport suite passed **91/91** immediately before the final Windows package was rebuilt.

The installed Windows package created from wallet implementation commit:

`212ee56d34aee578e6df701ef9f9a675661b7162`

passed its frozen-runtime self-test.

Final locally installed Windows EXE SHA-256 from that qualification:

`4F360D9F2C9DC51600B2C5D76FAA09364ADEF6762255D17F4DC528BDF3C069DD`

That hash identifies the locally qualified Windows package. GitHub-hosted Windows/Linux/macOS/iOS artifacts are separately built by GitHub Actions and therefore have their own artifact hashes.

## CI trigger

The cross-platform workflow runs on:

- manual dispatch;
- pushes to `main`;
- pushes to the wallet integration branch;
- relevant pull requests.

A failing platform job does not cancel the other platform jobs. Every published artifact must come from a successful platform job.
