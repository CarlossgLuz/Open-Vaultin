from vaultin.policy.engine import PolicyEngine
from vaultin.models import ActionContext, PolicyDecisionKind


def test_critical_policy_beats_user_request() -> None:
    engine = PolicyEngine.from_mapping({
        "critical": {"deny_actions": ["disable_governance"]},
        "project": {},
    })
    result = engine.evaluate(ActionContext(
        action="disable_governance",
        user_authorized=True,
        project_policy={},
    ))
    assert result.kind is PolicyDecisionKind.DENY


def test_project_policy_can_restrict_authorized_deploy() -> None:
    engine = PolicyEngine.from_mapping({"critical": {}, "project": {}})
    result = engine.evaluate(ActionContext(
        action="deploy",
        user_authorized=True,
        project_policy={"deny_actions": ["deploy"]},
    ))
    assert result.kind is PolicyDecisionKind.DENY
