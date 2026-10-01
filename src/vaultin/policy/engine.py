from copy import deepcopy
from typing import Any

from vaultin.models import ActionContext, PolicyDecision, PolicyDecisionKind


class PolicyEngine:
    def __init__(self, mapping: dict[str, Any]) -> None:
        self._mapping = deepcopy(mapping)

    @classmethod
    def from_mapping(cls, mapping: dict[str, Any]) -> "PolicyEngine":
        return cls(mapping)

    @staticmethod
    def _denied(action: str, policy: dict[str, Any]) -> bool:
        return action in set(policy.get("deny_actions", []))

    def evaluate(self, action: ActionContext) -> PolicyDecision:
        critical = self._mapping.get("critical", {})
        if self._denied(action.action, critical):
            return PolicyDecision(kind=PolicyDecisionKind.DENY, reason="critical Vaultin policy")

        project = {**self._mapping.get("project", {}), **action.project_policy}
        if self._denied(action.action, project):
            return PolicyDecision(kind=PolicyDecisionKind.DENY, reason="project policy")

        if self._denied(action.action, action.project_instructions):
            return PolicyDecision(kind=PolicyDecisionKind.DENY, reason="project-native instruction")

        if action.user_authorized:
            return PolicyDecision(kind=PolicyDecisionKind.ALLOW, reason="explicit user authorization")

        if action.action in set(action.agent_defaults.get("allow_actions", [])):
            return PolicyDecision(kind=PolicyDecisionKind.ALLOW, reason="agent default")

        return PolicyDecision(kind=PolicyDecisionKind.DENY, reason="no applicable authorization")
