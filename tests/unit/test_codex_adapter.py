from pathlib import Path

import pytest

from vaultin.adapters.codex import CodexAdapter
from vaultin.errors import GovernanceBlocked


class FakeProbe:
    def __init__(
        self,
        *,
        session_start=True,
        prompt_submit=True,
        pre_tool=True,
        post_tool=True,
        stop=True,
        mcp=True,
        timeout_semantics="fail-closed",
        complete_enforcement_boundary=False,
    ) -> None:
        self.values = locals() | {"client": "codex"}
        self.values.pop("self", None)

    def capabilities(self):
        return self.values


def test_codex_adapter_never_claims_full_enforcement_without_complete_boundary(tmp_path: Path) -> None:
    adapter = CodexAdapter(home=tmp_path, probe=FakeProbe(pre_tool=True, complete_enforcement_boundary=False))
    capabilities = adapter.detect()
    assert capabilities.governance_level == "partial"
    assert capabilities.fail_closed_ready is False


def test_missing_required_codex_gate_blocks_governed_session(tmp_path: Path) -> None:
    adapter = CodexAdapter(home=tmp_path, probe=FakeProbe(pre_tool=False))
    with pytest.raises(GovernanceBlocked, match="required Codex enforcement hook unavailable"):
        adapter.require_governed_mode()


def test_fail_open_hook_timeout_semantics_block_governed_mode(tmp_path: Path) -> None:
    adapter = CodexAdapter(home=tmp_path, probe=FakeProbe(pre_tool=True, timeout_semantics="fail-open"))
    with pytest.raises(GovernanceBlocked, match="hook timeout semantics are fail-open"):
        adapter.require_governed_mode()


def test_complete_boundary_can_report_full_governance(tmp_path: Path) -> None:
    adapter = CodexAdapter(home=tmp_path, probe=FakeProbe(complete_enforcement_boundary=True))
    capabilities = adapter.detect()
    assert capabilities.governance_level == "full"
    assert capabilities.fail_closed_ready is True
