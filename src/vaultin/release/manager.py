from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


Bump = Literal["none", "patch", "minor", "major"]


class PostUpdateResult(BaseModel):
    version: str
    healthy: bool
    rollback_to: str | None = None
    auto_update_suspended: bool = False
    reason: str | None = None


class ReleaseManager:
    KNOWLEDGE_PREFIXES = ("knowledge/", "memory/", "vaults/projects/", "docs/")

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.state_path = self.root / ".vaultin-runtime" / "release-state.json"

    @staticmethod
    def _runtime_change(path: str) -> bool:
        if path.startswith(ReleaseManager.KNOWLEDGE_PREFIXES):
            return False
        return path.startswith((
            "src/", "agents/", ".agents/skills/", "policies/", "workflows/",
            "scripts/", "adapters/", ".github/", "pyproject.toml", "AGENTS.md",
        ))

    def classify_change(self, paths: list[str], *, labels: list[str] | None = None) -> Bump:
        if not any(self._runtime_change(path) for path in paths):
            return "none"
        normalized = {label.casefold() for label in (labels or [])}
        if "breaking" in normalized or "major" in normalized:
            return "major"
        if "feature" in normalized or "minor" in normalized or "feat" in normalized:
            return "minor"
        return "patch"

    @staticmethod
    def next_version(current: str, bump: Bump) -> str:
        major, minor, patch = (int(part) for part in current.lstrip("v").split("."))
        if bump == "major":
            return f"{major + 1}.0.0"
        if bump == "minor":
            return f"{major}.{minor + 1}.0"
        if bump == "patch":
            return f"{major}.{minor}.{patch + 1}"
        return f"{major}.{minor}.{patch}"

    def _read_state(self) -> dict:
        if not self.state_path.is_file():
            return {"healthy_version": None, "auto_update_suspended": False}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _write_state(self, state: dict) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.state_path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(self.state_path)

    def record_healthy_version(self, version: str) -> None:
        state = self._read_state()
        state["healthy_version"] = version.lstrip("v")
        state["auto_update_suspended"] = False
        state.pop("last_failure", None)
        self._write_state(state)

    def auto_update_suspended(self) -> bool:
        return bool(self._read_state().get("auto_update_suspended", False))

    def handle_post_update_health(self, *, version: str, healthy: bool, reason: str | None = None) -> PostUpdateResult:
        state = self._read_state()
        if healthy:
            self.record_healthy_version(version)
            return PostUpdateResult(version=version, healthy=True, auto_update_suspended=False)
        previous = state.get("healthy_version")
        state["auto_update_suspended"] = True
        state["last_failure"] = {"version": version, "reason": reason or "healthcheck failed"}
        self._write_state(state)
        return PostUpdateResult(version=version, healthy=False, rollback_to=previous, auto_update_suspended=True, reason=reason or "healthcheck failed")
