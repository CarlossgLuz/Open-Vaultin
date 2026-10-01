import pytest

from vaultin.adapters.claude import ClaudeAdapter
from vaultin.adapters.gemini import GeminiAdapter
from vaultin.adapters.copilot import CopilotAdapter


class Probe:
    def __init__(self, **values):
        self.values = values

    def capabilities(self):
        return self.values


@pytest.mark.parametrize("adapter_cls,client", [
    (ClaudeAdapter, "claude"),
    (GeminiAdapter, "gemini"),
    (CopilotAdapter, "copilot"),
])
def test_secondary_adapter_reports_actual_not_codex_equivalent_level(adapter_cls, client) -> None:
    caps = adapter_cls(probe=Probe(context=True, mcp=True, hooks=True)).detect()
    assert caps.client == client
    assert caps.governance_level == "partial"
    assert caps.fail_closed_ready is False
    assert caps.complete_enforcement_boundary is False


def test_secondary_adapter_without_integration_is_context_only() -> None:
    caps = GeminiAdapter(probe=Probe(context=False, mcp=False, hooks=False)).detect()
    assert caps.governance_level == "context-only"
