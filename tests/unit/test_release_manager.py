from pathlib import Path

from vaultin.release.manager import ReleaseManager


def test_knowledge_only_change_has_no_runtime_release(tmp_path: Path) -> None:
    manager = ReleaseManager(tmp_path)
    assert manager.classify_change(["knowledge/appsec/foo.md"]) == "none"
    assert manager.classify_change(["vaults/projects/demo/runbook.md"]) == "none"


def test_runtime_bugfix_is_patch(tmp_path: Path) -> None:
    manager = ReleaseManager(tmp_path)
    assert manager.classify_change(["src/vaultin/policy/engine.py"], labels=["fix"]) == "patch"


def test_runtime_feature_is_minor(tmp_path: Path) -> None:
    manager = ReleaseManager(tmp_path)
    assert manager.classify_change(["src/vaultin/mcp/server.py"], labels=["feature"]) == "minor"


def test_breaking_runtime_contract_is_major(tmp_path: Path) -> None:
    manager = ReleaseManager(tmp_path)
    assert manager.classify_change(["src/vaultin/models.py"], labels=["breaking"]) == "major"


def test_failed_post_update_healthcheck_suspends_updates_and_returns_previous_version(tmp_path: Path) -> None:
    manager = ReleaseManager(tmp_path)
    manager.record_healthy_version("1.2.3")
    result = manager.handle_post_update_health(version="1.3.0", healthy=False, reason="health blocked")
    assert result.rollback_to == "1.2.3"
    assert result.auto_update_suspended is True
    assert manager.auto_update_suspended() is True
