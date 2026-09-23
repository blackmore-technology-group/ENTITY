# ENTITY v3 Regulatory Engineering Matrix

Date: 2026-09-23  
Classification: BTG INTERNAL ENGINEERING ANALYSIS  
Status: INTERNAL ENGINEERING MAPPING COMPLETE  

This document is an engineering control map, not legal advice, a regulator determination, a securities/commodity classification, or a finding that a particular deployment is compliant. External legal/regulatory validation remains required for each deployed venue, jurisdiction, asset class and settlement model.

## Core deployment doctrine

ENTITY v3 is protocol-neutral. A RIGHT, DCO, EEP instrument, EOPP participation right, settlement adapter or VALUE event SHALL NOT be labelled by the protocol as a security, commodity, payment instrument, legal title, personal-information consent, fair value, or verified external payment merely because a cryptographic record exists.

The deployment layer must carry jurisdiction, data classification, legal-basis/authority metadata, privacy controls, settlement model, disclosure requirements and external-classification status. Where classification is unresolved, the deployment state is `EXTERNAL_CLASSIFICATION_REQUIRED` and fail-closed policy may prohibit public listing or regulated settlement.
## Canada — federal privacy / electronic records

Authority baseline: Personal Information Protection and Electronic Documents Act (PIPEDA), current federal consolidation. Official source: https://laws-lois.justice.gc.ca/eng/acts/P-8.6/

Engineering mapping:
- data classification distinguishes personal from non-personal data before DCO listing;
- RIGHT records support purpose/action constraints rather than unrestricted possession;
- selective disclosure and encrypted claims reduce unnecessary disclosure;
- signed usage receipts provide accountable use evidence;
- revocation/status epochs provide deterministic stale-authority behaviour;
- provider-independent recovery preserves audit evidence without treating infrastructure custody as legal authority;
- retention/destruction policy remains deployment-controlled and SHALL NOT be inferred from immutable provenance alone.

Open external question: whether a particular data collection/use/disclosure has an adequate legal basis and an appropriate purpose is deployment-specific and requires legal/privacy review.
## British Columbia — private-sector privacy

Authority baseline: Personal Information Protection Act, SBC 2003 c.63. Official source: https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/00_03063_01

The BC consolidation reviewed was current to September 15, 2026. The legislative-change table also identifies amendments enacted but not in force until August 1, 2027; production policy must therefore be versioned by effective date rather than assuming future provisions are already operative.

Engineering mapping:
- jurisdiction/effective-date profile on listings and policies;
- consent/authority evidence can be attached without declaring the protocol itself to constitute valid consent;
- data-minimization and selective-disclosure controls;
- access/correction workflows represented as claims, challenges, supersession and consequences without deleting historical evidence;
- deployment-specific retention/deletion controls for underlying personal data.

External validation remains required for concrete BC personal-information processing and cross-jurisdiction transfers.
## European Union — GDPR

Authority baseline: Regulation (EU) 2016/679. Official source: https://eur-lex.europa.eu/eli/reg/2016/679/oj

Engineering mapping:
- purpose/action-limited RIGHT semantics support least-authority use rather than unrestricted data possession;
- selective disclosure, encrypted claims and relationship-specific pseudonyms support minimization;
- provenance and usage logs support accountability, but personal data should not be made permanently public merely to obtain provenance;
- deletion/erasure requirements are handled by separating immutable evidence/commitments from underlying data storage and by supersession/revocation where history must remain evidentiary;
- resolver and recovery profiles preserve controller/provider separation;
- cross-border transfer mechanisms are deployment policy, not protocol truth.

External controller/processor-role determination, lawful basis, DPIA requirements, data-subject-right implementation and transfer mechanism remain deployment-specific legal tasks.
## European Union — Data Act / Data Governance Act

Authority baselines:
- Regulation (EU) 2023/2854 (Data Act): https://eur-lex.europa.eu/eli/reg/2023/2854/oj
- Regulation (EU) 2022/868 (Data Governance Act): https://eur-lex.europa.eu/eli/reg/2022/868

Engineering mapping:
- EEP trades machine-verifiable rights in data rather than pretending copied bytes are inherently scarce;
- instrument/listing/disclosure records separate access, use, transfer, derivation and redistribution rights;
- provider-independent state and export/recovery support switching and portability goals;
- data-intermediation deployments can separate venue/operator identity from underlying data owner and from settlement provider;
- dispute/supersession and signed usage records preserve auditable rights history;
- EOPP is optional issuer policy, not a mandatory protocol toll.

External determination remains required as to whether a particular BTG or third-party venue is a regulated data-intermediation service and which Data Act duties apply to a given product/data relationship.

## European Union — AI Act

Authority baseline: Regulation (EU) 2024/1689. Official source: https://eur-lex.europa.eu/eli/reg/2024/1689/oj

Engineering mapping:
- AI authority profiles provide bounded capability, delegation depth, budget, expiry and cascading revocation;
- provenance and event records can preserve model/data/agent lineage and policy version used;
- data-governance and audit evidence can be attached to AI deployments;
- ENTITY does not classify an AI system's statutory risk category itself.

External role/risk classification and system-specific conformity obligations remain outside protocol truth.
## United States — FTC privacy/security baseline

Authority baseline: Federal Trade Commission business guidance on privacy and security. Official source: https://www.ftc.gov/business-guidance/privacy-security

Engineering mapping:
- privacy/security representations are evidence-backed rather than marketing-only assertions;
- least-authority RIGHT semantics and selective disclosure support minimization;
- signed access/use evidence and security-event history support accountability;
- retention and deletion remain explicit deployment policies;
- incident/recovery evidence supports response and continuity.

Sector-specific and state privacy laws must be assessed for each deployment. ENTITY does not declare a U.S. deployment compliant merely because these controls exist.

## Canada — money movement / AML boundary

Authority baselines:
- Proceeds of Crime (Money Laundering) and Terrorist Financing Act: https://laws-lois.justice.gc.ca/eng/acts/P-24.501/
- FINTRAC MSB registration guidance: https://fintrac-canafe.canada.ca/msb-esm/register-inscrire/reg-ins-eng

Engineering rule: ENTITY and EEP are not mandatory payment rails and require no cryptocurrency. Settlement adapters may reference bank, fiat, invoice, accounting, government, credit or token rails. External money movement is an attested fact, not protocol-generated truth.

If a venue deployment remits/transmits funds, deals in virtual currency, holds customer money or otherwise performs a regulated financial service, deployment must enter `EXTERNAL_FINANCIAL_REGULATORY_CLASSIFICATION_REQUIRED` until qualified counsel/regulatory analysis resolves applicable registration, KYC/recordkeeping/reporting and safeguarding duties.
## Securities / commodities / investment-contract boundary

No internal engineering test can determine legal classification of every EEP/EOPP instrument. The protocol therefore treats profit participation, reserve positions, royalties, transferable rights, indexes and derivative-value participation as contractual/economic records only.

Required deployment controls:
- `legal_classification_status` and `jurisdiction` on any public venue/instrument profile;
- fail-closed public listing where classification is unresolved and the venue policy requires classification;
- no protocol claim that a RIGHT is a share, security, commodity interest, derivative or deposit;
- disclosure of issuer, transferability, duration, payment obligations, valuation basis and risk;
- separation of indicative market marks from accounting fair value;
- surveillance records for self-trade, replay and manipulation indicators.

External securities/commodities counsel or regulator determination remains inherently external and cannot be closed by BTG engineering alone.

## Internal close-out status

BTG has closed the regulatory **engineering mapping** requirement when this matrix is paired with the released privacy, dispute, rights, settlement, recovery and evidence-boundary controls. The remaining legal/regulatory item is narrower: deployment-specific external classification/validation by appropriately qualified counsel, regulator or authority where required.
