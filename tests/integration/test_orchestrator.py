from pathlib import Path

import pytest

from vaultin.agents.registry import AgentRegistry
from vaultin.errors import GovernanceBlocked
from vaultin.knowledge.curator import KnowledgeCurator
from vaultin.ledger.store import LedgerStore
from vaultin.models import ExecutionState
from vaultin.orchestrator import Orchestrator, TaskRequest
from vaultin.policy.engine import PolicyEngine
from vaultin.routing.jev import RouteProposal
from vaultin.skills.catalog import SkillCatalog
from vaultin.workflow.state_machine import StateMachine


class StaticJev:
    def classify(self, task):
        return RouteProposal(
            task_type="implementation",
            domains=["backend"],
            risk="medium",
            agents=["software-engineer"],
            skills=[],
            workflow="implementation",
            confidence=0.95,
        )


class BrokenPolicyEngine:
    def evaluate(self, action):
        raise RuntimeError("policy backend unavailable")


def build_orchestrator(tmp_path: Path) -> Orchestrator:
    root = Path.cwd()
    return Orchestrator(
        root=root,
        ledger=LedgerStore(tmp_path / "vaultin.db"),
        policy_engine=PolicyEngine.from_mapping({"critical": {}, "project": {}}),
        state_machine=StateMachine.default(root),
        registry=AgentRegistry.load(root),
        skills=SkillCatalog.load(root),
        jev=StaticJev(),
        curator=KnowledgeCurator(),
    )


def test_orchestrator_records_required_lifecycle(tmp_path: Path) -> None:
    orchestrator = build_orchestrator(tmp_path)
    ctx = orchestrator.start(TaskRequest(
        client="codex",
        text="update API validation",
        cwd="/repo",
        user_authorized=True,
    ))
    orchestrator.mark_execution_started(ctx.execution_id)
    orchestrator.mark_validation(ctx.execution_id, "pytest", "PASS")
    result = orchestrator.finalize(ctx.execution_id, files_changed=["src/api.py"])

    assert result.state == ExecutionState.COMPLETED
    assert result.files_changed == ["src/api.py"]
    assert [event.kind for event in orchestrator.ledger.events(ctx.execution_id)] == [
        "INITIALIZING", "READY", "ROUTED", "EXECUTING",
        "VALIDATING", "CURATING", "COMMITTING", "SYNCING", "COMPLETED",
    ]


def test_orchestrator_blocks_when_policy_engine_unavailable(tmp_path: Path) -> None:
    orchestrator = build_orchestrator(tmp_path)
    orchestrator.policy_engine = BrokenPolicyEngine()
    with pytest.raises(GovernanceBlocked, match="policy validation unavailable"):
        orchestrator.start(TaskRequest(client="codex", text="read repo", cwd="/repo"))


def test_tool_authorization_uses_policy_precedence(tmp_path: Path) -> None:
    orchestrator = build_orchestrator(tmp_path)
    ctx = orchestrator.start(TaskRequest(client="codex", text="deploy app", cwd="/repo", user_authorized=True))
    orchestrator.policy_engine = PolicyEngine.from_mapping({"critical": {}, "project": {"deny_actions": ["deploy"]}})
    with pytest.raises(GovernanceBlocked, match="project policy"):
        orchestrator.authorize_tool(ctx.execution_id, action="deploy", user_authorized=True)
