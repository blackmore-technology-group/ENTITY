# Technical Note 001 — Three Verification Boundaries

**Status:** Informative  
**Applies to:** ENTITY v3.3.0  
**Steward:** Blackmore Technology Group Limited  
**Normative effect:** None. This note explains existing public design boundaries; it does not replace protocol or requirements documents.

## Abstract

ENTITY v3.3 separates three questions that are often collapsed in identity, provenance and evidence systems:

1. **Cryptographic verification** — was a specific record signed by the expected key over the expected bytes?
2. **Protocol verification** — is the signed record structurally and semantically valid under the applicable ENTITY rules?
3. **Reality/evidence verification** — what evidence supports an assertion about the external world, who supplied that evidence, under what authority, and what is the current contestable state of the claim?

The separation is intentional. A successful answer at one layer must not silently imply success at another.

## 1. Why the distinction matters

A signature can prove attribution to a key without proving that the signed statement is factually correct.

A protocol verifier can prove that a state transition obeys ENTITY rules without proving that a legal, physical, scientific, financial or other external-world assertion embedded in that state is true.

An external institution can provide evidence or an attestation without thereby becoming sovereign authority over an Entity's complete identity, rights or state.

ENTITY v3.3 therefore treats these as separate verification domains.

## 2. Cryptographic verification

Cryptographic verification asks questions such as:

- does the signature validate against the referenced public key?
- were the exact canonical bytes signed?
- is the expected signature algorithm/profile in use?
- is the key valid for the relevant signing operation under the protocol's key/authority state?

A positive cryptographic result means that the signature relationship has been verified within the stated cryptographic/profile assumptions.

It does **not** by itself establish:

- ownership;
- legal title;
- truth of a factual claim;
- authorization outside the key's granted scope;
- regulatory recognition;
- current validity if the signing authority has been revoked or otherwise constrained by applicable protocol rules.

## 3. Protocol verification

Protocol verification asks whether the record or transition obeys ENTITY semantics.

Typical questions include:

- is the record/schema valid?
- is the signer authorized for this transition?
- does delegation stay within its permitted scope?
- are revocation and historical-state rules respected?
- does a transition preserve identity continuity?
- are provider-independence and portability invariants maintained?
- are rights, usage or economic consequence transitions supported by the required protocol evidence?

Protocol validity therefore sits above raw signature validity.

A correctly signed transition can still be invalid if the signer lacks authority, the transition violates state-machine rules, or required prerequisites are absent.

## 4. Reality and evidence verification

ENTITY v3.3 introduces explicit structures for claims about the external world.

The relevant model can be summarized as:

```text
REALITY
  ↓
OBSERVATION
  ↓
CLAIM
  ↓
EVIDENCE
  ↓
ATTESTATION
  ↓
VERIFICATION
  ↓
AUTHORITATIVE ENTITY STATE
```

The purpose is not to make an external-world claim indisputable. The purpose is to make the basis of the claim attributable, typed, contestable and machine-verifiable.

Relevant questions include:

- who observed or asserted the fact?
- what evidence object supports it?
- what kind of claim is it?
- what authority did the attester have for this class of fact?
- is that authority still valid?
- does the evidence depend on an external registry, sensor, laboratory, receipt, document or API?
- has the claim been disputed, superseded, revoked or adjudicated?
- which downstream rights or economic consequences depend on it?

## 5. Typed claim states

ENTITY v3.3 defines typed states including:

- `OBSERVED`
- `ASSERTED`
- `INFERRED`
- `ATTESTED`
- `EXTERNALLY_VERIFIED`
- `ADJUDICATED`
- `DISPUTED`
- `REVOKED`
- `UNKNOWN`

These states are deliberately not interchangeable.

For example, `ATTESTED` indicates that an authorized attester has made or supported the claim within a stated authority scope. It does not mean the protocol has transformed the claim into universal truth.

`EXTERNALLY_VERIFIED` indicates that an external verification process or source supports the claim under the recorded evidence conditions. It does not make the external source sovereign authority over unrelated ENTITY state.

## 6. External anchors are evidence, not sovereignty

ENTITY may reference registries, APIs, sensors, institutions or other external systems as reality anchors.

That relationship must remain bounded.

An external source can provide:

- a value;
- a timestamped observation;
- a registry record;
- a certification result;
- a receipt;
- a laboratory result;
- an institutional attestation.

It does not automatically acquire the right to:

- control the Entity root;
- delegate arbitrary authority;
- redefine unrelated rights;
- replace the Entity's sovereign authorization chain;
- silently rewrite historical signed records.

## 7. Contestability and supersession

External-world claims can change, be challenged or be shown to be wrong.

ENTITY therefore preserves challenge and supersession instead of assuming that the latest accepted record erases the previous one.

A later claim can supersede an earlier claim while maintaining evidence of:

- what the earlier state was;
- who asserted it;
- what evidence supported it;
- who challenged it;
- what decision or new evidence caused the state to change.

This supports auditability without pretending that an earlier accepted claim was necessarily true merely because it was validly recorded.

## 8. Economic causality

ENTITY's data-rights and market model extends beyond provenance into usage and economic consequence.

The lifecycle remains:

```text
DCO
 ↓
Instrument
 ↓
Listing
 ↓
Disclosure
 ↓
Order / RFQ / Auction
 ↓
Price Discovery
 ↓
Trade
 ↓
Clearing
 ↓
Settlement
 ↓
Entitlement
 ↓
Usage
 ↓
Derived Output
 ↓
Economic Consequence
```

The v3.3 evidence layer allows downstream economic records to retain links to the evidence and claims that materially supported the authorized result.

This still does not mean every correlated event is causally attributable. Causal attribution must follow the rules and evidence represented by the protocol rather than being inferred from temporal proximity alone.

## 9. Security implications

Collapsing the three verification boundaries creates several dangerous failure modes:

- **signature-to-truth escalation:** treating a valid signature as proof a factual assertion is true;
- **protocol-to-law escalation:** treating protocol conformance as proof of legal title or regulatory recognition;
- **anchor-to-sovereignty escalation:** allowing an external data source to acquire control beyond its attestation scope;
- **provenance-to-rights escalation:** treating evidence of origin as proof of current rights;
- **usage-to-value escalation:** claiming realized economic value without the evidence required to support the consequence.

Security review should attempt to find implementation paths where these boundaries can be bypassed.

## 10. Public evidence and current limits

ENTITY v3.3 publishes a sealed 20-vector reality/evidence campaign and BTG-controlled cross-language reproducibility baselines.

Those results demonstrate controlled engineering reproducibility against the stated target. They do not constitute unrelated external implementation, independent security review, legal recognition or proof of market adoption.

The project therefore keeps the following external milestones separate:

- unrelated implementation/conformance;
- bidirectional interoperability;
- sovereign export/recovery across an independent implementation boundary;
- independent security review;
- deployment-specific legal/regulatory determinations;
- demonstrated external market participation/liquidity.

## Conclusion

ENTITY's v3.3 verification model is designed around a simple rule:

> A cryptographically valid statement is not automatically a protocol-valid statement, and a protocol-valid statement is not automatically a true statement about the external world.

Keeping those questions separate makes authority, evidence, contestability and downstream economic consequences easier to audit without turning infrastructure or signatures into authority they were never granted.
