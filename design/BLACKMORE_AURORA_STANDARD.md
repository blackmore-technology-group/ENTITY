# Blackmore Aurora — universal product design standard v1.0.0

**Owner:** Blackmore Technology Group. **Status:** post-v3.4.3 product-engineering candidate; not a protocol, rights or economic-policy revision.

## Identity

Blackmore Aurora is the shared visual and interaction system across **ENTITY**, **ENTITY Wallet**, the engineering orchestration product proposed as **Blackmore Nexus** (formerly BTG Command Centre), and the ENTITY public developer portal. Each product retains a functional role while reusing the same design primitives and safety states.

The Blackmore signature is a deep-navy instrumentation canvas, restrained luminous-cyan information hierarchy, mint integrity, violet AI capability, amber explicit-rights review and rose rejection. Controlled typography and accessible interactive affordances take precedence over aesthetic novelty. Never claim a compliance certification because a page looks refined.

### Source of truth

- `design/blackmore-aurora.tokens.json`: versioned portable semantic tokens.
- `tools/blackmore_aurora_qt.py`: native Qt stylesheet/palette adapter.
- `tools/entity_wallet_desktop.py`: commercial/authority wallet host and navigation.
- `tools/datachip_workspace_ui.py`: Qt visual Composer card/port palette.
- Public portal: matching `docs/assets/blackmore-aurora.css` and `blackmore-aurora.tokens.json` in ENTITY-DOCS.
- Blackmore Nexus: Tk host with matching colors and separate engineering-only device-support safety controls.

## Universal elements

1. **Product header:** mark and product identity, system role, truthful runtime status, primary action; never disguise pending gates.
2. **Navigation:** consistent left rail or compact mobile nav, a clear selected state, accessible keyboard order.
3. **Canvas:** dotted blueprint grid, categorized typed cards, explicit in/out sockets and inspected graph contracts.
4. **Inspection:** evidence, content hash, issuer status, authorization, failure reason, resource/time budget and host compatibility presented as separate values.
5. **Wallet:** distinct capability, rights, settlement and treasury states. Quotes must never look like completed settlements.
6. **Interfaces:** high contrast and touch targets >=44 px on touch UIs, visible focus, no color-only status; charts include units, legends and trustworthy zero/unknown states.
7. **Motion:** opacity and subtle translation for navigation only; reduced motion disables nonessential transitions.
8. **Device/safety:** no auto-executing unsigned code; no UI control may skip independent rights check. No design token may change a security decision.

## Colors and roles

| Role | HEX | Usage |
|:--|:--|:--|
| Foundation | `#08121F` | Desktop, web and mobile background |
| Canvas | `#0B1728` | DataChip graph / navigation |
| Surface | `#101F32` | Cards, drawers and documentation |
| Raised surface | `#142740` | Controls, toolbars |
| Stroke | `#29435F` | Component separation |
| Text | `#F4F8FF` | Essential text |
| Muted | `#9CB3CF` | Secondary explanations |
| Cyan | `#57D7F7` | Primary action and selection |
| Mint | `#65E8BD` | Independently verified content |
| Violet | `#CC9CFF` | AI/inference capability |
| Amber | `#F6C879` | Rights review / financial caution |
| Rose | `#FD8C9D` | Rejection / revocation |

Use `Segoe UI` with `Cascadia Code`/Consolas for hashes, identifiers and graph ports. Avoid distributing licensed font files.

## Shipping criteria

- CSS, Qt and Tk adapters resolve to exact semantic color tokens.
- Reflow tested at desktop widths 1440/1280, tablet 768, mobile 390; keyboard-only and reduced-motion support.
- UI screenshots inspected in both Wallet and Nexus, with dark/light platform contrast behavior; all critical actions testable.
- Existing ENTITY & Wallet conformance and market/rights business logic tests remain green.
- Application bundles explicitly include the matching theme files; fallback on missing resources is non-privileged.
- Public portal deployed via Pages and independently verified in a browser.
- Signed desktop and mobile release, publisher approval, secure deployment and production operations qualify separately.

**Naming decision:** use `Blackmore Nexus` as the **proposed outward-facing product name**, while retaining existing CLI, app IDs, ports, device enrollment and service identifiers until a controlled migration is approved.

**Release boundary:** this design rollout creates no new KMS key, financial instrument, issuer rights, third-party permission, deployment authority or value-state promotion.

## Native/mobile integration adapters (portable and deterministic)

- SwiftUI / iOS: `design/adapters/ios/BlackmoreAurora.swift`
- Android Jetpack Compose: `design/adapters/android/BlackmoreAurora.kt`
- TypeScript / React and Web Components: `design/adapters/web/aurora-tokens.ts`
- Portable CSS variables: `design/adapters/web/aurora-tokens.css`
- .NET desktop: `design/adapters/dotnet/BlackmoreAurora.cs`

Generate all adapters from the one token source with `python tools/generate_blackmore_aurora_adapters.py`; CI enforces `--check` for exact bytes. Platform hosts independently implement UI interactions, dynamic sizing and accessibility. Generated color constants are not an installed app, permission manifest or production runtime.

## First-party visual signature

The Blackmore B/mountain mark is the authentic asset already used by the public ENTITY documentation portal, not an approximate new logo. Wallet packages `design/assets/blackmore_mark.png` for native headers and application icons; Nexus packages the same PNG/ICO while preserving service identities and installed state. Avoid replacing it with a generated wordmark or distributing third-party fonts.
