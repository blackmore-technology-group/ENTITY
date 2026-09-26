from __future__ import annotations

import json

import pytest

from adam_v44 import ReactionIntent
from adam_v46 import ApplicationManifest, FieldMapping, UniversalApplicationNervousSystem
from test_v44_physics import make_intent


def manifest(app="OPS_APP"):
    return ApplicationManifest(
        application_id=app, version="1", entity_types=("PROJECT",), identity_namespace="ops-project",
        mappings=(FieldMapping("id", "EXTERNAL_ID", identity=True), FieldMapping("name", "HAS_NAME")),
        observable_scopes=("PUBLIC", "OPS"), permitted_reactions=("ASSIGN_EQUIPMENT",),
        constructible_forms=("json", "object", "sql_row", "document"),
    )


def test_application_ingest_preserves_exact_evidence_and_federates_identity(assignment_kernel):
    bus = UniversalApplicationNervousSystem(assignment_kernel)
    bus.register(manifest())
    raw = b'{"id":"204","name":"North Fork"}'
    event = bus.ingest("OPS_APP", raw, entity_type="PROJECT", external_id="204", authority="OPS", observed_at=1)
    canonical_id = bus.federation.resolve("ops-project", "204", "PROJECT")
    assert bus.exact_evidence[event.exact_hash] == raw
    assert json.loads(bus.construct("OPS_APP", canonical_id, "json"))["payload"]["name"] == "North Fork"


def test_app_cannot_propose_unlisted_reaction(assignment_kernel):
    bus = UniversalApplicationNervousSystem(assignment_kernel)
    bus.register(ApplicationManifest("READ_ONLY", "1", ("PROJECT",), "ro", (), permitted_reactions=()))
    with pytest.raises(PermissionError):
        bus.propose_reaction("READ_ONLY", make_intent(assignment_kernel))


def test_authorized_application_commits_reaction(assignment_kernel):
    bus = UniversalApplicationNervousSystem(assignment_kernel)
    bus.register(manifest())
    proof = bus.commit_reaction("OPS_APP", make_intent(assignment_kernel))
    assert proof.new_root == assignment_kernel.root


def test_application_constructions_are_deterministic(assignment_kernel):
    bus = UniversalApplicationNervousSystem(assignment_kernel)
    bus.register(manifest())
    bus.ingest("OPS_APP", b'{"id":"204","name":"North Fork"}', entity_type="PROJECT", external_id="204", authority="OPS", observed_at=1)
    cid = bus.federation.resolve("ops-project", "204", "PROJECT")
    assert bus.construct("OPS_APP", cid, "json") == bus.construct("OPS_APP", cid, "json")
