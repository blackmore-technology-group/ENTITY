# ENTITY Independent Node Program

Run an independently operated ENTITY test node and help test device-to-device communication, lineage preservation, multi-hop transfer, tamper detection, and recovery behavior.

> This is a **test network harness**, not a production trust network. A successful transport receipt proves that the participating test nodes exchanged the recorded bytes and hashes. It does not by itself prove external-world truth, legal ownership, economic value, or independent conformance with every ENTITY protocol requirement.

## Fast start — Windows

Requirements: Windows 10/11, PowerShell, Python 3.11+.

```powershell
git clone https://github.com/blackmore-technology-group/ENTITY.git
cd ENTITY
git checkout v3.4.3
powershell -ExecutionPolicy Bypass -File independent-node/install.ps1
python independent-node/node.py init
python independent-node/node.py status
python independent-node/node.py serve
```

The listener defaults to `127.0.0.1:8343`. To accept another device on your LAN, explicitly bind to an interface you control:

```powershell
python independent-node/node.py serve --host 0.0.0.0 --port 8343
```

Only expose the test listener on a network you trust. Do not expose it directly to the public Internet.

On a second machine:

```powershell
python independent-node/node.py init
python independent-node/node.py send --to http://DEVICE_A_IP:8343 --file independent-node/examples/sample-object.json
```

The sender and receiver each record privacy-minimized JSONL receipts under `.entity-independent-node/receipts/`.

## What is recorded

The harness creates a random pseudonymous test-node ID and records only protocol/test metadata needed for reproducibility: node ID, timestamps, receipt IDs, SHA-256 object hashes, origin hash, prior lineage hops, sender-declared node ID, receiver node ID, and verification outcome.

It does **not** intentionally collect usernames, passwords, private keys, machine inventory, browser history, personal documents, or unrelated files.

## Campaign

1. **Install / node identity** — initialize a fresh independent test node.
2. **A → B** — send an object and compare the sender/receiver receipts.
3. **A → B → C** — forward the received envelope and verify the origin hash survives every hop.
4. **Tamper test** — change the object after the envelope is created; the receiver must reject the mismatch.
5. **Restart** — stop/restart the node and verify its pseudonymous node ID and local receipt history persist.
6. **Offline handoff** — copy an envelope by removable media and use `verify` before forwarding.
7. **Cross-platform** — repeat across Windows/Linux/macOS where available.

See [TEST_CAMPAIGN.md](TEST_CAMPAIGN.md) and [PRIVACY.md](PRIVACY.md).

## Commands

```text
node.py init
node.py status
node.py serve [--host HOST] [--port PORT]
node.py send --to URL --file FILE
node.py verify --envelope FILE
node.py make-envelope --file FILE --out FILE
```

## Evidence boundary

This harness deliberately separates three claims:

- **BTG-controlled test:** BTG runs both endpoints.
- **External reproduction:** another operator runs the published harness and reproduces the expected result.
- **Independent interoperability evidence:** unrelated operators control different endpoints and exchange test objects.

Do not describe one category as another.

## Report a result

Open the Independent Node Program participation issue in the ENTITY repository and include:

- operating system (no serial numbers);
- ENTITY release/tag;
- test(s) attempted;
- node IDs if you are comfortable publishing them;
- receipt hashes;
- PASS/FAIL and the first reproducible failure;
- whether both endpoints were controlled by the same operator.

A failure is useful evidence. Please redact IP addresses, usernames, filesystem paths, tokens, keys, and personal data before posting.
