# ENTITY Exchange Protocol (EEP) — v3 Development Draft

Status: RELEASED / BTG INTERNAL QUALIFIED

EEP is a venue-neutral profile for markets in **rights to data and digital resources**. The underlying bytes are not assumed to be scarce. The instrument defines the scarce, transferable or non-transferable economic entitlement.

## Market object model

`DCO / ENTITY object` → `EEP instrument` → `listing` → `order or RFQ` → `trade` → `clearing obligation` → `payment-versus-right settlement` → `entitlement` → `usage event` → `revenue distribution`.

An instrument defines its underlying ENTITY object, instrument class, permitted rights, total units, transferability, duration, settlement currency and delivery mode. Initial classes are spot licence, subscription, compute-to-data, procurement, contribution and secondary licence.

## Venue neutrality

Any independent operator may create an EEP venue subject to its own jurisdiction and venue policy. A venue never becomes protocol authority. The same underlying ENTITY object and instrument semantics may be recognized by multiple independent venues.

## Execution

The reference profile supports deterministic price/time order-book matching and defines protocol identifiers for call auction and RFQ execution. Orders are replay-protected by nonce, constrained by lot/tick rules and signed by the participant. Sell orders reserve only held entitlements; secondary sale is rejected when transferability is disabled.

## Clearing and settlement

Execution creates a clearing obligation. Rights are not delivered merely because orders crossed. Settlement performs payment-versus-right transfer: the seller's entitlement balance is reduced, the buyer's is increased, and a signed buyer entitlement is issued. External payment verification is recorded separately from internal settlement state.

## Market data and surveillance

EEP publishes protocol-neutral market observations such as best bid, best ask, last trade and cumulative volume. These are observations, not protocol valuations. The surveillance reference detects at least self-cross/self-trade risk and is designed for extension to spoofing, wash trading, layering, unauthorized trading and venue-specific suspicious-activity policies.

## Disclosure and protected delivery

Disclosure records expose hashes and required metadata without requiring protected source data to be published. EEP can be paired with the PRIVACY profile and compute-to-data delivery so buyers can evaluate or exercise rights without receiving unrestricted raw copies.

## Regulatory boundary

EEP defines technical market semantics only. It does not classify an instrument as a security, commodity, derivative or other regulated product. Venue operators remain responsible for applicable legal classification, participant eligibility, market rules, disclosures and regulated settlement obligations in their jurisdictions.
## Signed intent and key-custody boundary

Participant and issuer-controlled market actions MUST be verifiable from signed intent without requiring a venue to possess the actor's private key. This includes instrument issuance, disclosure, listing, orders, cancellation, usage receipts, RFQs, quotes, quote acceptance and revenue-rule changes. Local signing helpers are reference conveniences only; they are not a requirement that a venue custody participant keys.

Order priority MUST use venue receipt time, not an untrusted client timestamp. The client timestamp remains part of the signed intent and audit trail, while `received_at_ms` determines price/time ordering.

## Settlement evidence

A payment reference alone MUST NOT cause EEP to claim externally verified money movement. `external_verified=true` requires a separately signed payment attestation bound to the trade and settlement reference, carrying evidence SHA-256 and an authority basis. The payer, payee, venue operator or an independently authorized settlement verifier may attest. The attestation is evidence and MUST NOT be represented as absolute truth.

## Listing and economic-control integrity

A listing MUST reference a disclosure hash already published for the same venue and instrument. Revenue-distribution rules MUST be issuer-signed and replay-protected; supplying an issuer ENTITY ID without a valid issuer signature does not authorize a rule change.

## Canonical signed-wire representation

EEP signed record bodies MUST use the canonical field types represented by `ENTITY_EXCHANGE_PROTOCOL.schema.json`. Integer fields are JSON integers, not numeric strings or floating-point values. Enumerated tokens and actions are canonical uppercase strings. SHA-256 values are 64-character lowercase hexadecimal strings.

For instrument rights, `actions` MUST be non-empty, unique and lexicographically sorted before signing. A recipient allocation map may contain zero or more recipients, but every basis-point value MUST be an integer greater than or equal to zero and the total MUST NOT exceed 10,000 basis points.

RFQ and quote expiry timestamps MUST be later than their signed creation timestamp. These cross-field and ordering rules are normative even when they cannot be expressed completely by JSON Schema.

A conforming implementation MUST reject a signed record whose cryptographic signature is valid over a non-canonical body if the body violates these wire rules. Implementations MUST NOT verify one representation and silently store or execute a normalized representation with different semantics.

## Conformance vectors

`protocol/v3/eep_vectors/VECTOR_MANIFEST.json` identifies the current development vector campaign. Vector validation uses two layers: JSON Schema Draft 2020-12 for exact record shape/types and the EEP canonical signed-wire rules for deterministic cross-field semantics.

`SHA256SUMS.txt` seals the schema, vector manifest and vector files. The vector campaign is development evidence only; external independent EEP interoperability remains pending.

## Execution commitment integrity

A sell entitlement MUST remain economically reserved from order acceptance through final settlement. Once an order or RFQ execution creates a pending clearing obligation, the executed quantity remains committed even if the originating order is already `FILLED`. A participant MUST NOT be permitted to offer the same units again while that clearing obligation remains pending.

RFQ quote acceptance MUST re-check the seller's unreserved entitlement at acceptance time. A quote that was valid when created MUST fail closed if intervening executions have committed the seller's available units.

Revenue-distribution terms are execution-time economics. Each executed trade MUST bind the then-active issuer-authenticated revenue rule set, including the empty rule set when none exists. Later rule changes MUST NOT retroactively alter the recipients or basis points of an already executed trade. Settlement and revenue distribution MUST use the trade-bound snapshot.

Concurrency is part of the execution invariant. A sell-availability check and the corresponding order admission MUST be one atomic critical section so simultaneous submissions cannot reserve the same units twice. Matching MUST revalidate executable order state under a write lock so concurrent matchers cannot create duplicate trades from the same orders.

Settlement MUST atomically revalidate the pending trade, transfer entitlement balances, issue the entitlement receipt, persist any bound revenue-distribution events and transition clearing/trade state. Concurrent settlement attempts MUST result in at most one committed settlement. A failure in revenue-event persistence MUST roll back the entitlement transfer and settlement state.
