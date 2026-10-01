from pydantic import BaseModel, ConfigDict


class VaultinSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    repository: str
    project_vault_owner: str
    project_vault_prefix: str = "vault-"
    fail_closed: bool = True
    runtime_dir_name: str = ".vaultin-runtime"

from enum import StrEnum
from typing import Any
from pydantic import Field


class PolicyDecisionKind(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class PolicyDecision(BaseModel):
    kind: PolicyDecisionKind
    reason: str


class ActionContext(BaseModel):
    action: str
    user_authorized: bool = False
    project_policy: dict[str, Any] = Field(default_factory=dict)
    project_instructions: dict[str, Any] = Field(default_factory=dict)
    agent_defaults: dict[str, Any] = Field(default_factory=dict)


class ExecutionState(StrEnum):
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    ROUTED = "ROUTED"
    EXECUTING = "EXECUTING"
    VALIDATING = "VALIDATING"
    CURATING = "CURATING"
    COMMITTING = "COMMITTING"
    SYNCING = "SYNCING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    BREAK_GLASS = "BREAK_GLASS"
    PENDING_SYNC = "PENDING_SYNC"
    PARTIAL_SYNC = "PARTIAL_SYNC"
    RETRYING_SYNC = "RETRYING_SYNC"
    ROLLED_BACK = "ROLLED_BACK"
