# ENTITY Originator Participation Profile (EOPP) — v3.0.0 Development Draft

Status: RELEASED / BTG INTERNAL QUALIFIED / OPTIONAL PROFILE / NOT QUALIFIED

## Purpose
EOPP defines how an originator or service provider may retain auditable economic participation while ENTITY Core and EEP remain open, issuer-neutral protocols. The scarce object is a verifiable RIGHT or entitlement, not a copy of the underlying bytes.

## Mandatory neutrality invariants
1. `protocol_tax_bps` MUST equal `0`.
2. No cryptocurrency or protocol token is required.
3. No issuer, including Blackmore Technology Group, receives hidden protocol privilege.
4. Every reserve or participation term MUST be disclosed, issuer-signed and versioned before the economic event to which it applies.
5. New terms MUST NOT create retroactive rights against completed transactions.
6. Internal ledger settlement MUST NOT be represented as externally verified payment without separate evidence.
7. Indicative market marks MUST NOT be represented as accounting fair value or protocol-created value.
8. Participation-policy effective times MUST move forward; a later version MUST NOT be applied retroactively to an earlier trade.
9. Initial treasury reserve allocation MUST occur at most once per EEP instrument unless a separately specified reserve-rebalance operation is used.
10. An obligation settlement attestation MUST come from the payer, the treasury owner/entity, or an independently authorized settlement verifier.
11. Economic-event capture and its monetary obligation MUST commit atomically; an event MUST NOT survive if its obligation write fails.
12. Initial reserve allocation MUST commit the EEP balance transfer and EOPP allocation record atomically across the two stores.

## Treasury record
A treasury binds an owner ENTITY to a distinct treasury ENTITY and a governance-policy hash. A dedicated treasury ENTITY is recommended so reserved EEP rights units are actually separated from public issuer inventory.

## Originator Participation Policy
A policy binds an EEP instrument to:
- total rights units;
- treasury reserve units;
- primary-proceeds treasury allocation in basis points;
- secondary-transfer originator royalty in basis points;
- derivative commercial participation in basis points;
- settlement currency;
- immutable terms hash and version.

The first version does not dictate economically appropriate percentages. Each issuer chooses and discloses its own terms, subject to venue and jurisdictional rules. Policy versions and effective times are monotonic. Trade-derived participation is resolved against the policy effective at the trade timestamp, so a later policy cannot rewrite the economics of an earlier settled trade.

## Reserve allocation
Reserve allocation MUST verify the EEP instrument issuer, total supply and currency against the signed participation policy. When the treasury ENTITY differs from the issuer, the reference implementation transfers the reserved EEP units into the treasury ENTITY balance. A reserve therefore represents an actual rights position, not merely an accounting label. The EEP balance movement and EOPP reserve-allocation record are one cross-store transaction: either both commit or neither commits. Policy versioning does not allocate the same reserve a second time. Once an instrument's initial reserve has been allocated, changing `reserve_units` requires an explicit future reserve-rebalance mechanism rather than silent reallocation.

## Primary and secondary transactions
For a settled EEP trade the reference implementation verifies the seller's original signed EEP order. The treasury service does not require the secondary seller's private key.

Primary allocation is a disclosed allocation within the issuer's gross proceeds. Secondary royalty is a disclosed contractual allocation within the secondary seller's gross proceeds in this profile version. Each captured trade is replay-protected by a unique economic-event key.

## Derivative participation
A derivative revenue event may create a contractual participation obligation using the signed policy's derivative basis points. The event is bound to the participation policy effective at its declared occurrence time, including historical policies after a later version exists, and its currency MUST match the signed policy unless a future conversion profile explicitly governs conversion. A derivative revenue assertion requires evidence. The reported gross revenue remains an evidenced assertion by the reporting actor; ENTITY does not infer revenue or legal liability from provenance alone.

## Service revenue
Treasury service-revenue events support listing, execution, clearing, settlement, market data, certification, managed infrastructure, API access, index licensing and other disclosed services. The provider may record its own receivable assertion without possessing the payer's private key; the payer remains the named obligation party, and settlement is a separate attested step. Provider revenue is commercial activity above the protocol and is not a mandatory ENTITY fee.

## Settlement evidence
An accrued economic obligation may be marked settled. `external_verified=true` requires a separate evidence hash and a verifier ENTITY attestation. The verifier must be the payer, the treasury owner/entity, or an independently authorized settlement verifier recorded by the treasury owner. The attestation records its authority basis and remains evidence, not absolute truth.

## Trade-capture reconciliation
EOPP provides a deterministic reconciliation view over settled EEP trades. For each trade that was in scope of an effective participation policy, the treasury can determine whether the corresponding replay-protected economic event has been captured, is missing, or disagrees with the settled clearing amount/currency. Reconciliation also verifies the expected obligation recipient, payer, amount, basis and basis-point rate; an event without its required obligation is incomplete. A complete reconciliation therefore provides evidence that trade capture is not silently omitting or corrupting primary or secondary participation events and receivables.

## Treasury position and market marks
Treasury position reports aggregate EEP reserve units and accrued/settled monetary obligations by currency. Indicative marks may use observed last, bid or ask prices, but MUST carry `indicative_only=true`, `not_accounting_fair_value=true`, and `not_protocol_generated_value=true`.

## BTG deployment
BTG uses this same public profile. Production activation requires a verified Blackmore Technology Group legal-entity ENTITY ID and a distinct BTG Treasury ENTITY ID supplied at deployment time. Neither identifier is hard-coded in the protocol or reference implementation.

## Regulatory neutrality
EOPP describes technical records and contractual economic mechanics. It does not classify an instrument as a security, commodity, derivative, licence or other regulated product. Each issuer and venue remains responsible for applicable legal and regulatory classification.
