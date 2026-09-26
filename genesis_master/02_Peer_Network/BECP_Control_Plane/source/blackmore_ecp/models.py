from enum import IntEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RiskLevel(IntEnum):
    READ = 10
    DIAGNOSTIC = 20
    CHANGE = 30
    PRIVILEGED = 40


class CapabilitySpec(BaseModel):
    name: str
    risk: RiskLevel
    description: str
    requires_approval: bool = False


class ActionRequest(BaseModel):
    actor: str
    role: str
    capability: str
    target: str = "local"
    params: dict[str, Any] = Field(default_factory=dict)
    approval_id: str | None = None
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))


class ActionResult(BaseModel):
    ok: bool
    capability: str
    target: str
    correlation_id: str
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class PolicyDecision(BaseModel):
    allowed: bool
    reason: str
    requires_approval: bool = False
