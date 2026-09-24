# ENTITY Global Passport SDK

The v3.4 Global Passport SDK is a thin public facade over ENTITY's existing sovereign primitives, v3.2 Rights Passports, v3.3 Evidence Objects and the v3.4 profile/continuous-ingestion layer.

It does **not** create authority, determine legal ownership, assert regulatory compliance, or make external standards subordinate to ENTITY.

Built-in aliases: `global`, `healthcare`, `finance`, `manufacturing`, `ai`, `robotics`, and public/unclassified `defence` / `defense`.

Typical flow:

```python
sdk.register_file("model.onnx", controller_entity_id, "ai", "healthcare")
```

The SDK automatically adds the global profile, resolves the profile stack fail-closed, registers the content-addressed artifact, creates evidence, creates the existing Rights Passport, creates the Global Passport, records provenance and writes a zero-value economic baseline unless real evidence supports a different state.
