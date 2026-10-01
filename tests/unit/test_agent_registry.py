from pathlib import Path

import pytest
import yaml

from vaultin.agents.registry import AgentRegistry, AgentRegistryError


CORE = {
    "orchestrator", "explorer", "software-engineer", "frontend-engineer",
    "platform-engineer", "security-reviewer", "qa-engineer",
    "code-reviewer", "release-manager", "knowledge-curator",
}


def _fixture_root(tmp_path: Path) -> Path:
    root = tmp_path
    (root / "agents/profiles").mkdir(parents=True)
    registry = {"version": 1, "agents": []}
    for name in sorted(CORE):
        profile = f"agents/profiles/{name}.yaml"
        registry["agents"].append({"name": name, "profile": profile})
        (root / profile).write_text(
            yaml.safe_dump({"name": name, "role": name, "preferred_skills": []}),
            encoding="utf-8",
        )
    (root / "agents/registry.yaml").write_text(yaml.safe_dump(registry), encoding="utf-8")
    return root


def test_every_registered_agent_has_profile(tmp_path: Path) -> None:
    registry = AgentRegistry.load(_fixture_root(tmp_path))
    assert registry.missing_profiles() == []


def test_registry_contains_only_approved_core_agents(tmp_path: Path) -> None:
    registry = AgentRegistry.load(_fixture_root(tmp_path))
    assert set(registry.names()) == CORE


def test_missing_profile_is_invalid_configuration(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    (root / "agents/profiles/explorer.yaml").unlink()
    with pytest.raises(AgentRegistryError, match="missing profile"):
        AgentRegistry.load(root)
