# ENTITY Wallet Identity & Lineage Onboarding

Status: wallet/application layer
ENTITY release compatibility: v3.4.3
Onboarding profile: `entity-wallet-onboarding-profile-v1`

## Purpose

A clean ENTITY Wallet installation must not assume the identity, lineage, organization, or economic authority of the machine on which it is installed.

The wallet therefore separates four concepts:

1. **Protocol origin** — the immutable historical ENTITY protocol origin.
2. **Principal ENTITY** — the person, business, organization, project, family, or community that the user creates during first-run setup, or that can be adopted from already-present valid ENTITY state.
3. **Operating ENTITY** — an optional organization/business/project under the principal that owns/controls the active wallet and DCOs.
4. **Device ENTITY** — the local computer installation used to authenticate and operate the wallet.

These are not interchangeable.

A device does not become a person. A public name does not become authority. Protocol origin does not become ownership of user assets.

## First-run flow

A clean desktop installation follows:

```
Install ENTITY Wallet
        ↓
Create separate Device ENTITY
        ↓
User creates Principal ENTITY
        ↓
Choose public .entity name
        ↓
Optionally create Operating ENTITY
        ↓
Establish signed user lineage
        ↓
Bind device to principal
        ↓
Create active wallet
        ↓
Enter ENTITY
```

Example:

```
jane.smith.entity
        ↓
acme.entity
        ↓
Acme participant wallet
```

The active wallet may be the root principal itself or the optional operating entity.

## Public names

A human-readable name such as:

```
jane.smith.entity
acme.entity
btg.entity
```

is a signed ENTITY name claim and display alias.

It is **not** the canonical database key and is not the source of authority.

The canonical identity remains the immutable Entity ID:

```
ent2-...
```

If two independent installations claim the same human-readable name, the identities remain distinct because their Entity IDs and signatures are distinct. A local name conflict is surfaced rather than silently granting first-claim ownership.

## User lineage

Wallet lineage is user-controlled identity/organization structure. It is not ENTITY protocol origin.

For example:

```
shawn.blackmore.entity → btg.entity
```

means the wallet profile has Shawn's person ENTITY as principal root and BTG as the active operating ENTITY.

Another installation could be:

```
jane.smith.entity → acme.entity
```

or simply:

```
independent.creator.entity
```

No BTG-specific identity is required.

When an operating organization is created beneath a principal, the relationship is explicitly signed and recorded through the Sovereign Authority registry. Device possession is recorded separately and does not infer ownership or identity.

## Device identity

ENTITY Wallet may automatically bootstrap a **system/device ENTITY** using installation and platform context.

The Device ENTITY may include:

- generated installation identifier;
- platform family;
- platform release;
- architecture;
- local device display name.

The device record explicitly states:

- device information is not user identity;
- device possession is not ownership;
- hardware attestation is not implied unless separately established.

The device never silently creates a human or organization identity.

## Wallet login

The desktop wallet uses a **device-bound signing-key login** rather than a centralized web username/password.

Unlock requires:

1. a valid signed wallet onboarding profile;
2. possession of the active ENTITY signing key;
3. possession of the bound Device ENTITY signing key;
4. successful challenge signatures from both identities.

The login challenge is fresh for each authentication attempt.

A new device therefore requires an explicit recovery/import/re-binding workflow rather than silently inheriting identity from the operating-system account. That recovery/import workflow is separate from the first-run identity-creation screen described here.

The onboarding layer itself does not add a separate password-based key-encryption scheme. Private-key protection remains the responsibility of the canonical identity/key-storage layer and any configured hardware/platform protection.

## Existing installations

Existing identities are adopted without regeneration.

For example the BTG production installation retains:

- Shawn Blackmore's existing person Entity ID;
- Blackmore Technology Group Limited's existing business Entity ID;
- the existing BTG workstation system Entity ID.

The wallet adds only the signed onboarding/profile bindings needed to express:

```
shawn.blackmore.entity → btg.entity
```

No DCO lineage, Global Passport, economic state, market history, or identity key is replaced by onboarding migration.

## Wallet presentation

The wallet header must resolve lineage from the active wallet profile.

It must never hard-code:

```
SHAWN → BTG → ENTITY
```

for arbitrary users.

The user lineage is shown separately from the ENTITY protocol and market context.

## Security and authority rules

- Public names are aliases, not authority.
- Entity IDs and signatures are authoritative.
- Device identity is separate from user identity.
- Device possession does not establish ownership.
- Protocol origin is separate from user lineage.
- Creating an identity does not create economic value.
- Creating a wallet does not create an instrument or listing.
- Creating an organization under a principal does not transfer unrelated rights.
- No cryptocurrency is required.
- Protocol tax remains zero.

## Cross-platform requirement

The onboarding path is part of the PySide6/Qt desktop wallet and is intended to operate consistently on:

- Windows;
- macOS;
- Linux.

Packaging must include the canonical identity, Sovereign Domain, Sovereign Authority, wallet, market, and passport modules required by first-run identity creation.
