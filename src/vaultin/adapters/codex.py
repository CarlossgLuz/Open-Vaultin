from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, Any

from vaultin.adapters.base import ClientCapabilities
from vaultin.errors import GovernanceBlocked


class CodexCapabilityProbe(Protocol):
    def capabilities(self) -> dict[str, Any]: ...


class FilesystemCodexProbe:
    """Conservative probe: local hooks can be detected, but never imply a complete boundary."""

    def __init__(self, home: Path) -> None:
        self.home = Path(home)

    def capabilities(self) -> dict[str, Any]:
        candidates = [
            self.home / ".codex" / "plugins" / "vaultin" / "hooks" / "hooks.json",
            self.home / ".codex" / "hooks" / "vaultin-hooks.json",
        ]
        hooks: dict[str, Any] = {}
        for path in candidates:
            if path.is_file():
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                    hooks = raw.get("hooks", raw) if isinstance(raw, dict) else {}
                except (json.JSONDecodeError, OSError):
                    hooks = {}
                break
        return {
            "client": "codex",
            "session_start": "SessionStart" in hooks,
            "prompt_submit": "UserPromptSubmit" in hooks,
            "pre_tool": "PreToolUse" in hooks,
            "post_tool": "PostToolUse" in hooks,
            "stop": "Stop" in hooks,
            "mcp": True,
            "timeout_semantics": "unknown",
            "complete_enforcement_boundary": False,
        }


class CodexAdapter:
    def __init__(self, *, home: Path, probe: CodexCapabilityProbe | None = None) -> None:
        self.home = Path(home)
        self.probe = probe or FilesystemCodexProbe(self.home)

    def detect(self) -> ClientCapabilities:
        raw = dict(self.probe.capabilities())
        required_context = bool(raw.get("session_start") and raw.get("prompt_submit"))
        pre_tool = bool(raw.get("pre_tool"))
        complete = bool(raw.get("complete_enforcement_boundary", False))
        timeout = raw.get("timeout_semantics", "unknown")
        if complete and required_context and pre_tool and timeout == "fail-closed":
            level = "full"
            ready = True
        elif required_context or pre_tool or raw.get("stop"):
            level = "partial"
            ready = False
        else:
            level = "context-only"
            ready = False
        return ClientCapabilities(
            client="codex",
            session_start=bool(raw.get("session_start")),
            prompt_submit=bool(raw.get("prompt_submit")),
            pre_tool=pre_tool,
            post_tool=bool(raw.get("post_tool")),
            stop=bool(raw.get("stop")),
            mcp=bool(raw.get("mcp")),
            governance_level=level,
            fail_closed_ready=ready,
            timeout_semantics=timeout,
            complete_enforcement_boundary=complete,
        )

    def require_governed_mode(self) -> ClientCapabilities:
        capabilities = self.detect()
        if not capabilities.pre_tool:
            raise GovernanceBlocked("required Codex enforcement hook unavailable")
        if capabilities.timeout_semantics == "fail-open":
            raise GovernanceBlocked("hook timeout semantics are fail-open")
        if not capabilities.complete_enforcement_boundary:
            raise GovernanceBlocked(
                "Codex hooks do not provide a complete enforcement boundary on this surface"
            )
        if not capabilities.fail_closed_ready:
            raise GovernanceBlocked("Codex governed mode is not fail-closed ready")
        return capabilities
