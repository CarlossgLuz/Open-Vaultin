from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import shutil
import subprocess

from vaultin.hooks.entrypoint import CodexHookController


ROOT = Path.cwd()


def _fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "Vaultin"
    root.mkdir()
    for file_name in ["vaultin.yaml"]:
        shutil.copy2(ROOT / file_name, root / file_name)
    for directory in ["agents", ".agents", "workflows"]:
        shutil.copytree(ROOT / directory, root / directory)
    (root / "policies").mkdir()
    (root / "policies/core.yaml").write_text(
        "critical:\n  deny_actions: [disable_governance]\n"
        "project:\n  deny_actions: [deploy]\n",
        encoding="utf-8",
    )
    return root


def _git_project(tmp_path: Path) -> Path:
    project = tmp_path / "demo"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    subprocess.run(["git", "-C", str(project), "config", "user.email", "hook@example.com"], check=True)
    subprocess.run(["git", "-C", str(project), "config", "user.name", "Vaultin Hook Test"], check=True)
    (project / "base.txt").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(project), "add", "."], check=True)
    subprocess.run(["git", "-C", str(project), "commit", "-qm", "initial"], check=True)
    return project


def test_real_hook_turn_creates_execution_and_receipt_automatically(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    project = _git_project(tmp_path)
    controller = CodexHookController(root=root, publish_receipts=False)

    start = controller.handle(
        event="session-start",
        payload={"session_id": "sess-1", "cwd": str(project), "source": "startup"},
    )
    assert start["continue"] is True

    prompt = controller.handle(
        event="prompt-submit",
        payload={
            "session_id": "sess-1",
            "turn_id": "turn-1",
            "cwd": str(project),
            "prompt": "fix failing backend test",
        },
    )
    assert "execution_id" in prompt["hookSpecificOutput"]["additionalContext"]
    assert "software-engineer" in prompt["hookSpecificOutput"]["additionalContext"]

    (project / "src.py").write_text("print('changed')\n", encoding="utf-8")

    initial_state = controller.session_store.load("sess-1")
    assert initial_state is not None and initial_state.execution_id
    execution_id = initial_state.execution_id

    controller.handle(
        event="post-tool",
        payload={
            "session_id": "sess-1",
            "turn_id": "turn-1",
            "cwd": str(project),
            "tool_name": "apply_patch",
            "tool_use_id": "tool-1",
            "tool_input": {"command": "*** Begin Patch"},
            "tool_response": {"ok": True},
        },
    )

    stop = controller.handle(
        event="stop",
        payload={
            "session_id": "sess-1",
            "turn_id": "turn-1",
            "cwd": str(project),
            "stop_hook_active": False,
            "last_assistant_message": "done",
        },
    )
    assert stop == {}

    state = controller.session_store.load("sess-1")
    assert state is not None
    assert state.execution_id is None
    assert state.receipt_path
    receipt = root / state.receipt_path
    assert receipt.is_file()
    record = controller.ledger.execution(execution_id)
    assert record.status == "COMPLETED"
    assert record.finished_at is not None


def test_completed_stop_records_original_response_without_echo_continuation(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    project = _git_project(tmp_path)
    controller = CodexHookController(root=root, publish_receipts=False)
    controller.handle(
        event="prompt-submit",
        payload={
            "session_id": "sess-completed",
            "turn_id": "turn-completed",
            "cwd": str(project),
            "prompt": "inspect backend",
        },
    )
    state = controller.session_store.load("sess-completed")
    assert state is not None and state.execution_id
    execution_id = state.execution_id

    stop = controller.handle(
        event="stop",
        payload={
            "session_id": "sess-completed",
            "turn_id": "turn-completed",
            "cwd": str(project),
            "stop_hook_active": False,
            "last_assistant_message": "Normal answer",
        },
    )

    assert stop == {}
    finished = controller.ledger.execution(execution_id)
    assert finished.status == "COMPLETED"
    assert finished.finished_at is not None
    observations = controller.ledger.events(execution_id)
    response_observation = next(
        event for event in observations if event.kind == "CODEX_FINAL_RESPONSE_OBSERVED"
    )
    assert response_observation.payload == {
        "present": True,
        "length": len("Normal answer"),
        "sha256": sha256("Normal answer".encode("utf-8")).hexdigest(),
    }
    final_state = controller.session_store.load("sess-completed")
    assert final_state is not None
    assert final_state.execution_id is None
    assert final_state.receipt_path
    assert (root / final_state.receipt_path).is_file()


def test_stop_recovers_inconsistent_context_without_continuation_loop(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    project = _git_project(tmp_path)
    controller = CodexHookController(root=root, publish_receipts=False)
    controller.handle(
        event="prompt-submit",
        payload={
            "session_id": "sess-inconsistent",
            "turn_id": "turn-inconsistent",
            "cwd": str(project),
            "prompt": "inspect backend",
        },
    )
    state = controller.session_store.load("sess-inconsistent")
    assert state is not None and state.execution_id
    execution_id = state.execution_id
    state.request = None
    controller.session_store.save(state)

    response = controller.handle(
        event="stop",
        payload={
            "session_id": "sess-inconsistent",
            "turn_id": "turn-inconsistent",
            "cwd": str(project),
            "stop_hook_active": False,
            "last_assistant_message": "Normal answer",
        },
    )

    assert "decision" not in response
    assert "session released" in response["systemMessage"]
    finished = controller.ledger.execution(execution_id)
    assert finished.status == "FAILED"
    assert finished.finished_at is not None
    recovered = controller.session_store.load("sess-inconsistent")
    assert recovered is not None
    assert recovered.execution_id is None


def test_duplicate_prompt_submit_reuses_same_execution(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    project = _git_project(tmp_path)
    controller = CodexHookController(root=root, publish_receipts=False)
    payload = {
        "session_id": "sess-duplicate",
        "turn_id": "turn-duplicate",
        "cwd": str(project),
        "prompt": "inspect backend",
    }

    first = controller.handle(event="prompt-submit", payload=payload)
    first_state = controller.session_store.load("sess-duplicate")
    assert first_state is not None and first_state.execution_id
    execution_id = first_state.execution_id

    second = controller.handle(event="prompt-submit", payload=payload)
    second_state = controller.session_store.load("sess-duplicate")

    assert second_state is not None
    assert second_state.execution_id == execution_id
    assert f"execution_id={execution_id}" in first["hookSpecificOutput"]["additionalContext"]
    assert f"execution_id={execution_id}" in second["hookSpecificOutput"]["additionalContext"]


def test_new_turn_recovers_orphaned_previous_execution(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    project = _git_project(tmp_path)
    controller = CodexHookController(root=root, publish_receipts=False)

    controller.handle(
        event="prompt-submit",
        payload={
            "session_id": "sess-orphan",
            "turn_id": "turn-1",
            "cwd": str(project),
            "prompt": "inspect backend",
        },
    )
    previous = controller.session_store.load("sess-orphan")
    assert previous is not None and previous.execution_id
    previous_execution = previous.execution_id

    response = controller.handle(
        event="prompt-submit",
        payload={
            "session_id": "sess-orphan",
            "turn_id": "turn-2",
            "cwd": str(project),
            "prompt": "now inspect frontend",
        },
    )

    old_record = controller.ledger.execution(previous_execution)
    assert old_record.status == "FAILED"
    assert old_record.finished_at is not None

    current = controller.session_store.load("sess-orphan")
    assert current is not None and current.execution_id
    assert current.execution_id != previous_execution
    assert current.turn_id == "turn-2"
    assert "execution_id=" in response["hookSpecificOutput"]["additionalContext"]


def test_interrupt_releases_active_execution(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    project = _git_project(tmp_path)
    controller = CodexHookController(root=root, publish_receipts=False)

    controller.handle(
        event="prompt-submit",
        payload={
            "session_id": "sess-interrupt",
            "turn_id": "turn-interrupt",
            "cwd": str(project),
            "prompt": "inspect backend",
        },
    )
    state = controller.session_store.load("sess-interrupt")
    assert state is not None and state.execution_id
    execution_id = state.execution_id

    response = controller.handle(
        event="interrupt",
        payload={
            "session_id": "sess-interrupt",
            "turn_id": "turn-interrupt",
            "cwd": str(project),
        },
    )

    assert response == {}
    finished = controller.ledger.execution(execution_id)
    assert finished.status == "FAILED"
    assert finished.finished_at is not None
    recovered = controller.session_store.load("sess-interrupt")
    assert recovered is not None
    assert recovered.execution_id is None


def test_receipt_publication_is_disabled_by_default(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("VAULTIN_PUBLISH_RECEIPTS", raising=False)
    root = _fixture_root(tmp_path)
    controller = CodexHookController(root=root)
    assert controller.publish_receipts is False


def test_pre_tool_infers_denied_action_from_real_bash_command(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    project = _git_project(tmp_path)
    controller = CodexHookController(root=root, publish_receipts=False)
    controller.handle(
        event="prompt-submit",
        payload={
            "session_id": "sess-2",
            "turn_id": "turn-2",
            "cwd": str(project),
            "prompt": "deploy app",
        },
    )

    response = controller.handle(
        event="pre-tool",
        payload={
            "session_id": "sess-2",
            "turn_id": "turn-2",
            "cwd": str(project),
            "tool_name": "Bash",
            "tool_use_id": "tool-2",
            "tool_input": {"command": "deploy --production"},
        },
    )
    assert response["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "project policy" in response["hookSpecificOutput"]["permissionDecisionReason"]


def test_explicit_implementation_route_allows_safe_tool_after_security_text(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    project = _git_project(tmp_path)
    controller = CodexHookController(root=root, publish_receipts=False)

    response = controller.handle(
        event="prompt-submit",
        payload={
            "session_id": "sess-explicit-implementation",
            "turn_id": "turn-explicit-implementation",
            "cwd": str(project),
            "prompt": (
                "workflow=implementation\n"
                "Implement the frontend security validation and review it afterwards."
            ),
        },
    )

    context = response["hookSpecificOutput"]["additionalContext"]
    assert "wf=implementation" in context
    assert "agent=frontend-engineer" in context

    pre_tool = controller.handle(
        event="pre-tool",
        payload={
            "session_id": "sess-explicit-implementation",
            "turn_id": "turn-explicit-implementation",
            "cwd": str(project),
            "tool_name": "apply_patch",
            "tool_use_id": "tool-explicit-implementation",
            "tool_input": {"command": "*** Begin Patch"},
        },
    )

    assert pre_tool == {}


def test_pre_tool_allows_without_permission_decision_or_updated_input(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    project = _git_project(tmp_path)
    controller = CodexHookController(root=root, publish_receipts=False)
    controller.handle(
        event="prompt-submit",
        payload={
            "session_id": "sess-allow",
            "turn_id": "turn-allow",
            "cwd": str(project),
            "prompt": "inspect backend",
        },
    )

    response = controller.handle(
        event="pre-tool",
        payload={
            "session_id": "sess-allow",
            "turn_id": "turn-allow",
            "cwd": str(project),
            "tool_name": "Bash",
            "tool_use_id": "tool-allow",
            "tool_input": {"command": "echo safe"},
        },
    )

    assert response == {}
    assert "permissionDecision" not in response
    assert "updatedInput" not in response


def test_pre_tool_denies_when_policy_validation_fails(tmp_path: Path, monkeypatch) -> None:
    root = _fixture_root(tmp_path)
    project = _git_project(tmp_path)
    controller = CodexHookController(root=root, publish_receipts=False)
    controller.handle(
        event="prompt-submit",
        payload={
            "session_id": "sess-policy-failure",
            "turn_id": "turn-policy-failure",
            "cwd": str(project),
            "prompt": "inspect backend",
        },
    )

    def fail_policy(*args, **kwargs):
        raise RuntimeError("policy engine unavailable")

    monkeypatch.setattr(controller.policy_engine, "evaluate", fail_policy)

    response = controller.handle(
        event="pre-tool",
        payload={
            "session_id": "sess-policy-failure",
            "turn_id": "turn-policy-failure",
            "cwd": str(project),
            "tool_name": "Bash",
            "tool_use_id": "tool-policy-failure",
            "tool_input": {"command": "echo safe"},
        },
    )

    hook_output = response["hookSpecificOutput"]
    assert hook_output["permissionDecision"] == "deny"
    assert "policy validation unavailable" in hook_output["permissionDecisionReason"]
    assert "updatedInput" not in hook_output


def test_route_context_is_compact_and_does_not_echo_full_prompt(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    project = _git_project(tmp_path)
    controller = CodexHookController(root=root, publish_receipts=False)
    prompt_text = "inspect backend and keep hook context minimal"

    response = controller.handle(
        event="prompt-submit",
        payload={
            "session_id": "sess-compact",
            "turn_id": "turn-compact",
            "cwd": str(project),
            "prompt": prompt_text,
        },
    )

    context = response["hookSpecificOutput"]["additionalContext"]
    assert len(context) <= 128
    assert prompt_text not in context
    assert "wf=" in context
    assert "agent=" in context


def test_jev_timeout_is_bounded_for_prompt_hook(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "placeholder-value")
    monkeypatch.setenv("VAULTIN_JEV_TIMEOUT_SECONDS", "999")
    root = _fixture_root(tmp_path)
    controller = CodexHookController(root=root, publish_receipts=False)

    classifier = controller._jev(agent_names=["software-engineer"], skill_names=[])

    assert classifier.timeout_seconds == 5.0


def test_invalid_jev_timeout_uses_safe_default(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "placeholder-value")
    monkeypatch.setenv("VAULTIN_JEV_TIMEOUT_SECONDS", "invalid")
    root = _fixture_root(tmp_path)
    controller = CodexHookController(root=root, publish_receipts=False)

    classifier = controller._jev(agent_names=["software-engineer"], skill_names=[])

    assert classifier.timeout_seconds == 3.0


def test_pre_tool_without_execution_context_allows_safe_bootstrap(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    project = _git_project(tmp_path)
    controller = CodexHookController(root=root, publish_receipts=False)

    response = controller.handle(
        event="pre-tool",
        payload={
            "session_id": "sess-bootstrap",
            "turn_id": "turn-bootstrap",
            "cwd": str(project),
            "tool_name": "Bash",
            "tool_use_id": "tool-bootstrap",
            "tool_input": {"command": "git status --short"},
        },
    )

    assert response == {}


def test_pre_tool_without_execution_context_still_enforces_policy(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    project = _git_project(tmp_path)
    controller = CodexHookController(root=root, publish_receipts=False)

    response = controller.handle(
        event="pre-tool",
        payload={
            "session_id": "sess-bootstrap-deny",
            "turn_id": "turn-bootstrap-deny",
            "cwd": str(project),
            "tool_name": "Bash",
            "tool_use_id": "tool-bootstrap-deny",
            "tool_input": {"command": "deploy --production"},
        },
    )

    assert response["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "project policy" in response["hookSpecificOutput"]["permissionDecisionReason"]


def test_session_start_recovers_inherited_active_execution(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    project = _git_project(tmp_path)
    controller = CodexHookController(root=root, publish_receipts=False)

    controller.handle(
        event="prompt-submit",
        payload={
            "session_id": "sess-restarted",
            "turn_id": "turn-old",
            "cwd": str(project),
            "prompt": "inspect backend",
        },
    )
    previous = controller.session_store.load("sess-restarted")
    assert previous is not None and previous.execution_id
    previous_execution = previous.execution_id

    response = controller.handle(
        event="session-start",
        payload={
            "session_id": "sess-restarted",
            "cwd": str(project),
            "source": "startup",
        },
    )

    assert response["continue"] is True
    finished = controller.ledger.execution(previous_execution)
    assert finished.status == "FAILED"
    assert finished.finished_at is not None
    recovered = controller.session_store.load("sess-restarted")
    assert recovered is not None
    assert recovered.execution_id is None
