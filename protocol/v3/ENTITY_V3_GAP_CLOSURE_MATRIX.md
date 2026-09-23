# ENTITY v3 Gap Closure Matrix

Status: RELEASE EVIDENCE / BTG INTERNAL QUALIFIED

| Gap | Implemented v3 mechanism | Current evidence |
|---|---|---|
| Core vs extensions | Immutable core + versioned profile registry/negotiation | `ProfileRegistry`, profile architecture draft |
| Conflict/dispute | Claim/challenge/evidence/ruling/supersession/consequence ledger | History-preservation test |
| Privacy | Selective disclosure, encrypted claim envelope, pairwise pseudonyms | Disclosure + AES-GCM + pseudonym tests |
| Key compromise/recovery | Signed status `COMPROMISED`, recovery quorum, succession designation | Status + quorum + succession tests |
| Resolution consistency | Signed resolver views, epoch/TTL, quorum, anti-equivocation | Two-resolver + equivocation test |
| Revocation propagation | Signed monotonic status epochs, TTL and stale policies | Revoked/stale deterministic test |
| Rights vocabulary | Canonical ontology, implied-right closure, prerequisite prohibition propagation, deny-by-default | Directionality/non-overblocking test + reference/mirror convergence |
| Derived value | Separate attribution methodology/evaluator/confidence/evidence | Methodology receipt test |
| Settlement neutrality | Adapter registry for multiple rails | Adapter implementation |
| Physical binding | Hardware binding, clone suspicion, custody/rebind/tamper event model | Physical custody test |
| AI delegation | Depth, capability, budget/time attenuation, cascading kill | Delegation/kill test |
| Time | Signed timestamp attestation, validity/TTL/epoch semantics | Status/time implementation |
| Schema evolution | Immutable historical schemas + compatibility metadata + negotiation | Mutation rejection test |
| Abuse/spam | Reputation-neutral fixed-window resource quotas | Admission rejection test |
| Operational degradation | Explicit NORMAL/OFFLINE_VERIFY/STALE_READ/READ_ONLY/RECOVERY states | Operation-permission test |
| Standards governance | Signed RFCs with multi-party threshold voting | Two-vote acceptance test |
| Developer adoption | Existing verifier + new profile drafts/tests; profile negotiation | Full unittest suite |
| Existing-system migration | Explicit non-authoritative bridges for OIDC/X.509/DID/VC/DNS/C2PA/ERP/PKI/etc. | Bridge test |
| Performance economics | Merkle batching and archival snapshot proof semantics | Merkle proof + snapshot test |
| Originator economic participation | EOPP issuer-defined treasury reserve, primary/secondary/derivative/service participation; no protocol tax/token; external settlement remains evidence-backed attestation | 20 EOPP tests including atomicity, historical-policy binding, reconciliation and BTG non-privilege boundary |
| Data market infrastructure | EEP instruments/listing/order/match/clear/settle/entitle/use/revenue/surveillance/RFQ/call auction plus signed non-custodial participant/issuer actions, venue-receipt priority, evidence-backed payment attestations, disclosure-bound listings, unsettled-right reservation, execution-time revenue-rule binding, atomic concurrent admission/matching/settlement and revenue rollback | Full trade + auction + RFQ + signed-intent/concurrency/adversarial campaigns + 16 reference/mirror convergence tests |

| Market-state survivability | Signed provider-independent EEP/EOPP logical-state bundle, per-table/database roots, controller attestations, required trade-revenue bindings, empty-target restore and atomic cross-database rollback | 6 destructive/tamper/rollback behaviors + self-verifying recovery evidence manifest |

## Remaining qualification work

Implementation is not qualification. Before v3 can be described as a released interoperable protocol, each profile requires normative JSON Schemas/test vectors, negative campaigns, recovery/destructive-state tests, load qualification, independent clean-room implementations and cross-language live interoperability. Privacy primitives require dedicated cryptographic review; market-surveillance coverage requires adversarial campaigns; and legal/regulatory classifications remain outside protocol truth.
