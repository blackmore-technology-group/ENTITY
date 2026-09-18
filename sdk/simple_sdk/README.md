# ENTITY Simple SDK v1

This facade is the developer-facing reduction of ENTITY. It does not create a second authority layer; every operation delegates to the existing canonical identity, principal-binding, Open SDK and portability authorities.

Primary developer surface:

```text
create_entity
create_application
pair_device
register_asset
record_event
export_entity
```

Verification/revocation helpers are `verify_pairing`, `verify_export`, and `revoke_device`.

The SDK deliberately does **not** expose direct settlement, payment, verified-rights, corporate-capital or sovereign-authority mutation. Those remain canonical governed transitions.

`export_entity` is a signed portable export. The facade does not yet label this a complete `Move My Entity` workflow because target-provider import plus retained controller-key continuity must be proven end to end before that UI claim is made.
