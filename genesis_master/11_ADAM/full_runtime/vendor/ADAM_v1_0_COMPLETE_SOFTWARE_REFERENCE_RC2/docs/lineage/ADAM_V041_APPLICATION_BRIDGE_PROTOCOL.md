# ADAM v0.41 Universal Application Bridge Protocol

## Purpose

Applications do not surrender their user interfaces or business logic. They surrender independent authoritative data ownership where an ADAM domain has been adopted.

Each application becomes a boundary organ that:

1. sends observations or requested reactions to ADAM;
2. receives temporary constructed views;
3. discards or caches those views without becoming authoritative.

## Registration manifest

```json
{
  "app_id": "crm",
  "entity_type": "CUSTOMER",
  "id_field": "customer_id",
  "identity_namespace": "enterprise-customer",
  "authority": "ENTERPRISE",
  "security_domain": "ORGANIZATION",
  "fields": [
    {"external_field": "name", "relation": "HAS_NAME", "value_type": "STRING"},
    {"external_field": "status", "relation": "HAS_STATUS", "value_type": "STRING"}
  ]
}
```

Applications using the same identity namespace, entity type, authority and external identity converge on the same entity atom.

## JSON-RPC methods

- `health`
- `bridge.register`
- `bridge.upsert`
- `bridge.construct`
- `cognition.interpret`
- `reaction.register`
- `reaction.propose`
- `reaction.simulate`
- `reaction.commit`
- `aql.execute`
- `sql.execute`

## Security

The HTTP principal is supplied through `X-ADAM-Principal`. Production deployments must bind this to real authentication and purpose-bound grants rather than trusting a raw header.

## Side effects

An application observation may be atomized immediately. A business side effect must be represented as a registered reaction and pass governance before commit.
