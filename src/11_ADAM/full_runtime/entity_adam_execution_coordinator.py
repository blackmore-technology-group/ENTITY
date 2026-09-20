from __future__ import annotations
from typing import Any


def niki_accept_action_proposal_v2(*, executor, full_runtime, proposal: dict, request_id: str, capability_id: str, agent_id: str, handler, policy_id: str | None = None) -> dict[str, Any]:
    execution = executor.execute(proposal, request_id=request_id, capability_id=capability_id, agent_id=agent_id, handler=handler, policy_id=policy_id)
    subject = str(proposal.get("subject_entity_id") or proposal.get("actor_entity_id") or proposal.get("object_ref") or agent_id)
    transition = full_runtime.record_authorized_transition(entity_id=subject, entity_kind=str(proposal.get("subject_entity_kind") or "ENTITY_ACTION_SUBJECT"), event_type=str(proposal.get("operation") or proposal.get("action") or "ADAM_ACTION"), event={"proposal": dict(proposal), "request_id": request_id, "capability_id": capability_id, "agent_id": agent_id, "policy_id": policy_id}, authorization_receipt={"authorized": bool(execution.get("authorized")), "authority_root": "ENTITY", "request_id": execution.get("request_id"), "capability_id": execution.get("capability_id"), "agent_id": execution.get("agent_id"), "policy_id": execution.get("policy_id"), "evidence_sha256": execution.get("evidence_sha256"), "outcome": execution.get("outcome")}, result=execution.get("result"))
    return {"schema": "niki-adam-action-handoff-v2", "status": "EXECUTED_AND_ADAM_ATOMICALLY_RECORDED", "execution": execution, "adam_transition": transition, "authority_root": "ENTITY", "executor": "ADAM", "reasoner": "NIKI"}
