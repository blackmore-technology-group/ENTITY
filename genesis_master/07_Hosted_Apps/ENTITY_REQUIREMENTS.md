# ENTITY Hosted Apps Requirements
Source: SERS-ENTITY-003 Complete Master Engineering Design v2.2
Status: Authoritative repository requirement mapping

## Application Authority
- Every hosted application SHALL have explicit, revocable scopes.
- Application authority SHALL not automatically propagate to ENTITY, ADAM, BSIE or unrelated applications.
- Apps SHALL receive only the minimum data projection and capability needed for their declared purpose.

## Packages and Updates
- App packages SHOULD carry provenance, hashes, signatures, dependency/SBOM information and Rights Bill of Materials data.
- Updates SHALL preserve version history and SHALL NOT silently reinterpret historical signed events.
- App permissions SHALL be re-evaluated when an update materially changes requested scope or purpose.

## Data and Actions
- App data SHALL follow Entity classification and vault policy.
- State-changing operations SHALL pass authoritative policy authorization.
- Repeated signed requests SHALL not cause duplicate high-impact operations.
- Hosted apps SHALL not infer commercialization rights from mere file possession or access.
- Untrusted app content SHALL never directly determine Entity authority.
