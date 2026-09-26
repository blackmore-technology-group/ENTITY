# ENTITY Security Requirements
Source: SERS-ENTITY-003 Complete Master Engineering Design v2.2
Status: Authoritative repository requirement mapping

## Cryptography and Keys
- Cryptographic algorithms SHALL be explicitly identified and versioned; architecture SHALL be crypto-agile.
- Root/recovery keys SHOULD use hardware-backed protection where available.
- Operational keys SHALL support rotation and revocation without changing sovereign identity.
- Private keys SHALL never be written to event ledgers.

## Threat Model
- Qualification SHALL cover stolen devices/keys, malicious guardians/peers, Sybil, replay, equivocation, duplicate settlement, agent/connector compromise, prompt injection, exfiltration, ransomware, vault theft, metadata correlation, fake provenance, fraudulent synthetic data, unauthorized sublicensing, payment reversal and network partition.
- Prompt-injected instructions from untrusted content SHALL never determine Entity authority.
- Sensitive AI disclosure SHALL evaluate read permission, classification, provider, purpose, minimum necessary context and disclosure policy.

## Authentication and Trust
- Implement strong authentication, session expiration, device authorization/revocation, rate limits, secure token handling and high-trust mutual authentication where appropriate.
- Security-sensitive failures SHALL fail closed and SHALL NOT leak secrets.
- High-impact key use SHOULD support step-up authentication and auditable key-use events.
