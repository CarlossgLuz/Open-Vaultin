from pathlib import Path

from vaultin.hooks.entrypoint import HookRuntime
from vaultin.policy.engine import PolicyEngine


def test_pre_tool_hook_denies_when_policy_denies(tmp_path: Path) -> None:
    runtime = HookRuntime(
        root=tmp_path,
        policy_engine=PolicyEngine.from_mapping({"critical": {}, "project": {"deny_actions": ["deploy"]}}),
    )
    response = runtime.handle(
        event="pre-tool",
        payload={"tool_name": "shell", "tool_input": {"command": "deploy"}, "action": "deploy"},
    )
    assert response["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "project policy" in response["hookSpecificOutput"]["permissionDecisionReason"]


def test_pre_tool_hook_allows_without_permission_decision_or_updated_input(tmp_path: Path) -> None:
    runtime = HookRuntime(root=tmp_path, policy_engine=PolicyEngine.from_mapping({"critical": {}, "project": {}}))

    response = runtime.handle(
        event="pre-tool",
        payload={"tool_name": "shell", "tool_input": {"command": "echo safe"}},
    )

    assert response == {}
    assert "permissionDecision" not in response
    assert "updatedInput" not in response


def test_session_start_returns_developer_context(tmp_path: Path) -> None:
    runtime = HookRuntime(root=tmp_path, policy_engine=PolicyEngine.from_mapping({"critical": {}, "project": {}}))
    response = runtime.handle(event="session-start", payload={"cwd": str(tmp_path), "source": "startup"})
    assert response["continue"] is True
    assert "Vaultin" in response["hookSpecificOutput"]["additionalContext"]


def test_resolve_root_accepts_utf8_bom_marker(tmp_path: Path, monkeypatch) -> None:
    from vaultin.hooks.entrypoint import resolve_root

    home = tmp_path / "home"
    target = tmp_path / "Vaultin"
    target.mkdir()
    marker = home / ".vaultin" / "root"
    marker.parent.mkdir(parents=True)
    marker.write_bytes(("\ufeff" + str(target) + "\r\n").encode("utf-8"))

    monkeypatch.delenv("VAULTIN_ROOT", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    assert resolve_root() == target.resolve()


def test_stop_entrypoint_error_never_requests_continuation(tmp_path: Path, monkeypatch, capsys) -> None:
    import io
    import json
    import sys
    import vaultin.hooks.entrypoint as entrypoint

    class BrokenController:
        def __init__(self, *, root):
            pass

        def handle(self, *, event, payload):
            raise RuntimeError("finalization exploded")

    monkeypatch.setattr(entrypoint, "CodexHookController", BrokenController)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"session_id": "s", "turn_id": "t"})))

    code = entrypoint.main(["stop", "--root", str(tmp_path)])
    output = json.loads(capsys.readouterr().out)

    assert code == 0
    assert "decision" not in output
    assert "without continuation" in output["systemMessage"]


def test_pre_tool_entrypoint_error_remains_fail_closed(tmp_path: Path, monkeypatch, capsys) -> None:
    import io
    import json
    import sys
    import vaultin.hooks.entrypoint as entrypoint

    class BrokenController:
        def __init__(self, *, root):
            pass

        def handle(self, *, event, payload):
            raise RuntimeError("policy unavailable")

    monkeypatch.setattr(entrypoint, "CodexHookController", BrokenController)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"session_id": "s"})))

    code = entrypoint.main(["pre-tool", "--root", str(tmp_path)])
    captured = capsys.readouterr()

    assert code == 2
    assert "Vaultin hook blocked" in captured.err
