from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from vaultin.adapters.base import ClientCapabilities


class SecondaryProbe(Protocol):
    def capabilities(self) -> dict[str, Any]: ...


class StaticFilesystemProbe:
    def __init__(self, *, client: str, home: Path) -> None:
        self.client = client
        self.home = Path(home)

    def capabilities(self) -> dict[str, Any]:
        if self.client == "gemini":
            extension = self.home / ".gemini" / "extensions" / "vaultin" / "gemini-extension.json"
            context = self.home / ".gemini" / "GEMINI.md"
            return {"context": context.exists() or extension.exists(), "mcp": extension.exists(), "hooks": False}
        if self.client == "copilot":
            hooks = self.home / ".copilot" / "hooks"
            return {"context": False, "mcp": False, "hooks": hooks.exists()}
        if self.client == "claude":
            context = self.home / ".claude" / "CLAUDE.md"
            return {"context": context.exists(), "mcp": False, "hooks": False}
        return {"context": False, "mcp": False, "hooks": False}


class SecondaryAdapter:
    client: str

    def __init__(self, *, home: Path | None = None, probe: SecondaryProbe | None = None) -> None:
        self.home = home or Path.home()
        self.probe = probe or StaticFilesystemProbe(client=self.client, home=self.home)

    def detect(self) -> ClientCapabilities:
        raw = dict(self.probe.capabilities())
        integrated = bool(raw.get("context") or raw.get("mcp") or raw.get("hooks"))
        return ClientCapabilities(
            client=self.client,
            session_start=bool(raw.get("hooks")),
            prompt_submit=bool(raw.get("hooks")),
            pre_tool=bool(raw.get("hooks")),
            post_tool=bool(raw.get("hooks")),
            stop=bool(raw.get("hooks")),
            mcp=bool(raw.get("mcp")),
            governance_level="partial" if integrated else "context-only",
            fail_closed_ready=False,
            timeout_semantics="unknown",
            complete_enforcement_boundary=False,
        )
