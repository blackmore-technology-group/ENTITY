# Independent Node Program — Privacy and Safety

The Independent Node Program is designed for voluntary interoperability testing with pseudonymous node identifiers.

## Data minimization

The reference harness stores test state locally by default. Receipt records contain test identifiers, timestamps, SHA-256 hashes, lineage hops, endpoint role and PASS/FAIL information. The harness does not require a participant's real name, email address, GitHub account, hardware serial number, private signing key, personal files or machine inventory.

## Network safety

The listener binds to `127.0.0.1` by default. Binding to `0.0.0.0` is an explicit operator choice. Use a trusted LAN, VPN, isolated test network or other controlled environment. Do not port-forward the reference listener to the public Internet.

The reference listener limits request size and accepts only the Independent Node test endpoint. It is not a production server.

## Public evidence

Before posting receipts or logs, remove IP addresses, local usernames, absolute paths, access tokens, private keys, secrets and personal information. Public participation is voluntary.

## Claim boundary

A receipt establishes what the harness observed. It does not establish legal ownership, external-world truth, regulatory compliance, monetary value, payment, endorsement, or full protocol conformance unless separately demonstrated.
