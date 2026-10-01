from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ClientCapabilities(BaseModel):
    client: str
    session_start: bool = False
    prompt_submit: bool = False
    pre_tool: bool = False
    post_tool: bool = False
    stop: bool = False
    mcp: bool = False
    governance_level: Literal["full", "partial", "context-only"] = "context-only"
    fail_closed_ready: bool = False
    timeout_semantics: Literal["fail-closed", "fail-open", "unknown"] = "unknown"
    complete_enforcement_boundary: bool = False
