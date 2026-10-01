# ENTITY Independent Node Test Campaign v1

Target: current supported ENTITY release. Historical releases may be tested only when clearly labelled.

## INP-01 — Installation and persistence

Initialize a fresh node, record its pseudonymous node ID, restart the process, and confirm `status` reports the same ID.

Expected: PASS with persistent local state.

## INP-02 — Two-device exchange

Operator A starts a listener. Operator B sends the sample object.

Expected: B receives an HTTP 200 receipt; A records the same object SHA-256 and origin SHA-256; receiver lineage contains the new A/B hop as appropriate.

Record whether A and B are independently controlled.

## INP-03 — Three-device lineage

A creates an envelope, B receives/verifies it, then B forwards the received envelope to C.

Expected: the original `origin_sha256` is unchanged and each hop appends rather than rewrites prior lineage.

## INP-04 — Tamper rejection

Create an envelope, then alter `object` without updating `object_sha256`.

Expected: `verify` fails and a receiver rejects the envelope.

## INP-05 — Restart/recovery

Exchange at least one object, restart the receiving node, and inspect status/receipts.

Expected: node identity and locally written evidence remain available.

## INP-06 — Offline handoff

Use `make-envelope` to write an envelope to disk, move it to another device without network transport, and run `verify`.

Expected: hash and lineage verification PASS.

## INP-07 — Cross-platform

Repeat INP-02 across different operating systems.

Expected: byte/hash semantics remain identical.

## Evidence classification

Every published result must state one of:

- `BTG_CONTROLLED`
- `EXTERNAL_REPRODUCTION`
- `INDEPENDENT_MULTI_OPERATOR`

The classification describes operator independence, not correctness.

## Suggested result record

```json
{
  "campaign": "ENTITY-INP-v1",
  "test": "INP-02",
  "entity_release": "v3.4.3",
  "classification": "INDEPENDENT_MULTI_OPERATOR",
  "platform_a": "Windows 11",
  "platform_b": "Linux",
  "receipt_sha256": "...",
  "result": "PASS"
}
```

Do not include secrets, IP addresses, serial numbers, personal identifiers, or private filesystem paths.
