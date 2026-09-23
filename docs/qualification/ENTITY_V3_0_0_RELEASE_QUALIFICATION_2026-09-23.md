# ENTITY v3.0.0 Release Qualification - 2026-09-23

Status: **BTG INTERNALLY QUALIFIED FOR OPEN-SOURCE RELEASE**

ENTITY v3.0.0 is qualified for release within the evidence scope recorded here. This qualification does not claim unrelated-third-party v3 reimplementation, legal title determination, regulatory classification, market valuation, or absolute truth of external settlement evidence.

## Qualified architecture

The release preserves the five universal primitives:

- ENTITY - what exists;
- AUTHORITY - who may act;
- RIGHT - what may be done;
- EVENT - what happened;
- VALUE - what economic consequence was recorded.

The qualified release includes the Universal Transaction Fabric, versioned profiles, ENTITY Exchange Protocol (EEP), ENTITY Originator Participation Profile (EOPP), and Market State Recovery Profile (MSRP).
## Release evidence

- Complete v3 regression: **90/90 PASS** on the pre-release qualified tree.
- EEP schema/wire conformance: **4/4 PASS**.
- EEP reference/mirror convergence: **16/16 PASS**.
- Targeted EEP authorization/execution hardening: **30/30 PASS**.
- Targeted EOPP economic-participation campaign: **20/20 PASS**.
- Targeted MSRP destructive/tamper/rollback campaign: **7/7 PASS**.
- EEP vector campaign: **27 vectors** - 13 expected valid and 14 expected invalid.
- Bounded release-load gate: **500 fully settled trades** across the reference and qualification-mirror EEP implementations.

The bounded release-load run completed 250 trades per implementation using signed orders, matching, clearing, settlement and entitlement transfer. On the qualification laptop, the reference implementation completed approximately 14.35 trades/s and the qualification mirror approximately 13.70 trades/s. These measurements are evidence of bounded release execution, not production capacity certification.
## Market-integrity invariants qualified

- participant and issuer actions are verified from signed intent without venue custody of their private keys;
- venue receipt time, not client time, determines price/time priority;
- listings are bound to published disclosures;
- externally verified payment state requires signed payment evidence;
- seller rights committed to an unsettled trade remain reserved;
- RFQ acceptance re-checks unreserved seller entitlement;
- revenue-distribution policy is bound at trade execution and cannot be rewritten after execution;
- concurrent sell admission, matching and settlement are serialized/atomic;
- a failed revenue-event write rolls the settlement transaction back;
- market recovery requires controller attestations and survives destructive EEP/EOPP database loss;
- rehashing a tampered recovery bundle does not defeat controller-signature verification.

## Economic boundary

EOPP does not impose an ENTITY protocol tax, does not require a cryptocurrency, and gives BTG no hidden protocol privilege. Treasury participation arises from disclosed issuer rights, reserves, contractual participation, or commercial services. Indicative market marks are not protocol-declared fair value.
## Release claim boundary

The following remain outside this release qualification:

- unrelated third-party v3 clean-room implementation;
- cross-language live v3 interoperability beyond the BTG Python reference/mirror evidence;
- production exchange capacity, availability or regulatory certification;
- legal ownership/title determination;
- securities, commodities, privacy or other jurisdictional regulatory classification;
- independent cryptographic review of every privacy primitive;
- proof that an external bank/payment event is objectively true rather than attested evidence.

These are post-release qualification tracks, not hidden assumptions. ENTITY v3.0.0 is released as an open protocol and reference implementation with BTG-internal qualification evidence for the scope above.
