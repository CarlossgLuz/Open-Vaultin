import json
import sys
import uuid

import httpx
import pytest

from vaultin.agents.registry import AgentProfile, AgentRegistry
from vaultin.hooks.entrypoint import CodexHookController
from vaultin.ledger.receipt import ReceiptData, ReceiptWriter
from vaultin.routing.fallback import FallbackRouter
from vaultin.routing.jev import (
    HttpJevClassifier,
    RouteProposal,
    RoutingError,
    SubprocessJevClassifier,
    TaskInput,
    route_task,
    validate_route,
)
from vaultin.skills.catalog import SkillCatalog, SkillMetadata


def core_registry() -> AgentRegistry:
    names = [
        "orchestrator", "explorer", "software-engineer", "frontend-engineer",
        "platform-engineer", "security-reviewer", "qa-engineer", "code-reviewer",
        "release-manager", "knowledge-curator",
    ]
    return AgentRegistry.from_profiles([AgentProfile(name=name, role=name, preferred_skills=[]) for name in names])


def empty_catalog() -> SkillCatalog:
    return SkillCatalog.from_skills([])


def _choice_answer(choice: str, options: list[str], confidence: float = 0.95) -> dict:
    probabilities = {option: 0.0 for option in options}
    probabilities[choice] = 1.0
    return {
        "type": "choice",
        "choice": choice,
        "probabilities": probabilities,
        "confidence": confidence,
    }


def _jev_response(
    confidence: float = 0.95,
    *,
    confidences: dict[str, float] | None = None,
    skill: str | None = None,
) -> dict:
    decisions = confidences or {}
    answers = {
        "task_type": _choice_answer(
            "implementation",
            ["implementation", "security-review", "qa", "code-review", "exploration"],
            decisions.get("task_type", confidence),
        ),
        "domain": _choice_answer(
            "backend",
            ["backend", "frontend", "security", "qa", "platform", "release", "knowledge", "unknown"],
            decisions.get("domain", confidence),
        ),
        "primary_agent": _choice_answer(
            "software-engineer",
            core_registry().names(),
            decisions.get("primary_agent", confidence),
        ),
        "risk": _choice_answer(
            "medium",
            ["low", "medium", "high", "critical"],
            decisions.get("risk", confidence),
        ),
        "workflow": _choice_answer(
            "implementation",
            ["implementation", "security-review", "qa", "code-review", "exploration"],
            decisions.get("workflow", confidence),
        ),
    }
    if skill is not None:
        answers["skill"] = _choice_answer(
            skill,
            ["none", "safe-change-protocol", "qa-validation"],
            decisions.get("skill", confidence),
        )
    return {
        "model": "jev-1.13.0",
        "answers": answers,
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }


def _response(*, status_code: int = 200, payload: dict | None = None, content: bytes | None = None) -> httpx.Response:
    request = httpx.Request("POST", "https://api.typesafe.ai/v1/systemone")
    if content is not None:
        return httpx.Response(status_code, content=content, request=request)
    return httpx.Response(status_code, json=payload, request=request)


def _test_credential() -> str:
    return uuid.uuid4().hex


def _route_with_http_jev(monkeypatch, response, *, credential: str | None = None) -> RouteProposal:
    monkeypatch.setenv("TYPESAFE_API_KEY", credential or _test_credential())
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: response)
    return route_task(
        TaskInput(text="fix the backend API validation"),
        jev=HttpJevClassifier(agent_names=core_registry().names()),
        registry=core_registry(),
        skills=empty_catalog(),
    )


def test_jev_result_is_rejected_if_agent_is_not_registered() -> None:
    proposal = RouteProposal(task_type="implementation", domains=["backend"], risk="medium", agents=["imaginary-agent"], skills=[], workflow="implementation", confidence=0.99)
    with pytest.raises(RoutingError, match="unregistered agent"):
        validate_route(proposal, registry=core_registry(), skills=empty_catalog())


def test_low_confidence_jev_uses_deterministic_fallback() -> None:
    class FakeJev:
        def classify(self, task: TaskInput) -> RouteProposal:
            return RouteProposal(task_type="unknown", domains=[], risk="low", agents=["explorer"], skills=[], workflow="exploration", confidence=0.2)

    result = route_task(TaskInput(text="fix failing backend test"), jev=FakeJev(), registry=core_registry(), skills=empty_catalog())
    assert result.source == "fallback"
    assert "software-engineer" in result.agents


def test_invalid_jev_output_falls_back_without_expanding_authority() -> None:
    class BrokenJev:
        def classify(self, task: TaskInput) -> RouteProposal:
            raise ValueError("bad JSON")

    result = route_task(TaskInput(text="review this security finding"), jev=BrokenJev(), registry=core_registry(), skills=empty_catalog())
    assert result.source == "fallback"
    assert result.agents == ["security-reviewer"]


def test_fallback_unknown_task_routes_to_explorer() -> None:
    result = FallbackRouter().route(TaskInput(text="understand this unfamiliar repository"))
    assert result.agents == ["explorer"]
    assert result.source == "fallback"


def test_explicit_implementation_overrides_security_terms_without_calling_jev() -> None:
    class MustNotRunJev:
        def classify(self, task: TaskInput) -> RouteProposal:
            raise AssertionError("JEV must not classify an explicit workflow")

    result = route_task(
        TaskInput(
            text=(
                "workflow=implementation\n"
                "Implement the frontend change and run a security review afterwards."
            )
        ),
        jev=MustNotRunJev(),
        registry=core_registry(),
        skills=empty_catalog(),
    )

    assert result.workflow == "implementation"
    assert result.source == "explicit"
    assert result.agents == ["frontend-engineer"]


def test_explicit_implementation_survives_exploration_review_words() -> None:
    class MustNotRunJev:
        def classify(self, task: TaskInput) -> RouteProposal:
            raise AssertionError("JEV must not classify an explicit workflow")

    result = route_task(
        TaskInput(
            text=(
                "workflow = implementation\n"
                "Investigate, review and analyse the backend, then implement the fix."
            )
        ),
        jev=MustNotRunJev(),
        registry=core_registry(),
        skills=empty_catalog(),
    )

    assert result.workflow == "implementation"
    assert result.agents == ["software-engineer"]


def test_explicit_workflow_is_case_and_whitespace_tolerant() -> None:
    class MustNotRunJev:
        def classify(self, task: TaskInput) -> RouteProposal:
            raise AssertionError("JEV must not classify an explicit workflow")

    result = route_task(
        TaskInput(text="  WORKFLOW = IMPLEMENTATION  \nfix backend"),
        jev=MustNotRunJev(),
        registry=core_registry(),
        skills=empty_catalog(),
    )

    assert result.workflow == "implementation"
    assert result.source == "explicit"


def test_invalid_explicit_workflow_fails_closed() -> None:
    class MustNotRunJev:
        def classify(self, task: TaskInput) -> RouteProposal:
            raise AssertionError("JEV must not classify an invalid explicit workflow")

    with pytest.raises(RoutingError) as error:
        route_task(
            TaskInput(text="workflow=destroy-everything\nfix backend"),
            jev=MustNotRunJev(),
            registry=core_registry(),
            skills=empty_catalog(),
        )

    assert error.value.reason == "invalid_explicit_workflow"


def test_prompt_workflow_precedes_handoff_metadata() -> None:
    class MustNotRunJev:
        def classify(self, task: TaskInput) -> RouteProposal:
            raise AssertionError("JEV must not classify an explicit workflow")

    result = route_task(
        TaskInput(
            text="workflow=implementation\nfix backend",
            metadata={"workflow": "security-review"},
        ),
        jev=MustNotRunJev(),
        registry=core_registry(),
        skills=empty_catalog(),
    )

    assert result.workflow == "implementation"
    assert result.agents == ["software-engineer"]


def test_handoff_metadata_precedes_jev_when_prompt_has_no_directive() -> None:
    class MustNotRunJev:
        def classify(self, task: TaskInput) -> RouteProposal:
            raise AssertionError("JEV must not classify trusted handoff workflow")

    result = route_task(
        TaskInput(
            text="continue the change",
            metadata={"workflow": "implementation"},
        ),
        jev=MustNotRunJev(),
        registry=core_registry(),
        skills=empty_catalog(),
    )

    assert result.workflow == "implementation"
    assert result.source == "explicit"


def test_http_jev_valid_response_routes_with_jev_source(monkeypatch) -> None:
    calls: dict = {}

    def fake_post(url, *, headers, json, timeout):
        calls.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _response(payload=_jev_response())

    credential = _test_credential()
    monkeypatch.setenv("TYPESAFE_API_KEY", credential)
    monkeypatch.setattr(httpx, "post", fake_post)

    result = route_task(
        TaskInput(text="fix the backend API validation"),
        jev=HttpJevClassifier(agent_names=core_registry().names()),
        registry=core_registry(),
        skills=empty_catalog(),
    )

    assert result.source == "jev"
    assert result.agents == ["software-engineer"]
    assert result.decision_confidences == {
        "task_type": 0.95,
        "domain": 0.95,
        "primary_agent": 0.95,
        "risk": 0.95,
        "workflow": 0.95,
    }
    assert result.decision_probabilities["domain"]["backend"] == 1.0
    assert calls["url"] == "https://api.typesafe.ai/v1/systemone"
    assert calls["headers"]["Authorization"] == f"Bearer {credential}"
    assert calls["json"]["model"] == "jev-latest"


def test_missing_typesafe_api_key_uses_fallback(monkeypatch) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    result = route_task(
        TaskInput(text="fix the backend API validation"),
        jev=HttpJevClassifier(agent_names=core_registry().names()),
        registry=core_registry(),
        skills=empty_catalog(),
    )
    assert result.source == "fallback"
    assert result.agents == ["software-engineer"]


def test_http_jev_timeout_uses_fallback(monkeypatch) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", _test_credential())

    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(httpx, "post", timeout)
    result = route_task(
        TaskInput(text="fix the backend API validation"),
        jev=HttpJevClassifier(agent_names=core_registry().names()),
        registry=core_registry(),
        skills=empty_catalog(),
    )
    assert result.source == "fallback"


@pytest.mark.parametrize("status_code", [401, 500])
def test_http_jev_http_failure_uses_fallback(monkeypatch, status_code: int) -> None:
    result = _route_with_http_jev(monkeypatch, _response(status_code=status_code))
    assert result.source == "fallback"


def test_http_jev_invalid_json_uses_fallback(monkeypatch) -> None:
    result = _route_with_http_jev(monkeypatch, _response(content=b"not-json"))
    assert result.source == "fallback"


def test_http_jev_invalid_schema_uses_fallback(monkeypatch) -> None:
    result = _route_with_http_jev(monkeypatch, _response(payload={"answers": {}}))
    assert result.source == "fallback"
    assert result.fallback_reason == "jev_schema_error"


def test_http_jev_low_confidence_uses_fallback(monkeypatch) -> None:
    result = _route_with_http_jev(monkeypatch, _response(payload=_jev_response(confidence=0.2)))
    assert result.source == "fallback"


def test_low_confidence_secondary_domain_does_not_discard_route(monkeypatch) -> None:
    response = _jev_response(
        confidences={"domain": 0.21, "primary_agent": 0.95, "workflow": 0.95}
    )
    response["answers"]["domain"] = _choice_answer(
        "unknown",
        ["backend", "frontend", "security", "qa", "platform", "release", "knowledge", "unknown"],
        0.21,
    )
    result = _route_with_http_jev(monkeypatch, _response(payload=response))

    assert result.source == "jev"
    assert result.domains == ["unknown"]
    assert result.decision_confidences["domain"] == 0.21
    assert result.uncertain_decisions == ["domain"]


def test_low_confidence_agent_uses_selective_fallback_reason(monkeypatch) -> None:
    response = _jev_response(confidences={"primary_agent": 0.2, "workflow": 0.95})
    result = _route_with_http_jev(monkeypatch, _response(payload=response))

    assert result.source == "fallback"
    assert result.fallback_reason == "low_agent_confidence"


def test_low_confidence_workflow_uses_selective_fallback_reason(monkeypatch) -> None:
    response = _jev_response(confidences={"primary_agent": 0.95, "workflow": 0.2})
    result = _route_with_http_jev(monkeypatch, _response(payload=response))

    assert result.source == "fallback"
    assert result.fallback_reason == "low_workflow_confidence"


def test_http_jev_fallback_reason_is_safe_and_contains_no_secret(monkeypatch, caplog) -> None:
    caplog.set_level("INFO", logger="vaultin.routing.jev")
    credential = _test_credential()
    result = _route_with_http_jev(
        monkeypatch,
        _response(status_code=500),
        credential=credential,
    )

    serialized = json.dumps(result.model_dump(mode="json"))
    assert result.fallback_reason == "jev_http_error"
    assert credential not in serialized
    assert "reason=jev_http_error" in caplog.text
    assert credential not in caplog.text


def test_missing_api_key_has_structured_fallback_reason(monkeypatch) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    result = route_task(
        TaskInput(text="fix the backend API validation"),
        jev=HttpJevClassifier(agent_names=core_registry().names()),
        registry=core_registry(),
        skills=empty_catalog(),
    )

    assert result.source == "fallback"
    assert result.fallback_reason == "missing_api_key"


def test_http_jev_uses_only_catalog_skills(monkeypatch) -> None:
    catalog = SkillCatalog.from_skills([
        SkillMetadata(name="safe-change-protocol", description="safe changes"),
        SkillMetadata(name="qa-validation", description="test validation"),
    ])
    response = _jev_response(skill="safe-change-protocol")
    monkeypatch.setenv("TYPESAFE_API_KEY", _test_credential())
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: _response(payload=response))

    result = route_task(
        TaskInput(text="fix the backend API validation"),
        jev=HttpJevClassifier(
            agent_names=core_registry().names(),
            skill_names=catalog.names(),
        ),
        registry=core_registry(),
        skills=catalog,
    )

    assert result.source == "jev"
    assert result.skills == ["safe-change-protocol"]


def test_http_jev_skill_question_uses_only_catalog_options(monkeypatch) -> None:
    catalog = SkillCatalog.from_skills([
        SkillMetadata(name="safe-change-protocol", description="safe changes"),
        SkillMetadata(name="qa-validation", description="test validation"),
    ])
    calls: dict = {}

    def fake_post(url, *, headers, json, timeout):
        calls["json"] = json
        return _response(payload=_jev_response(skill="safe-change-protocol"))

    monkeypatch.setenv("TYPESAFE_API_KEY", _test_credential())
    monkeypatch.setattr(httpx, "post", fake_post)
    HttpJevClassifier(
        agent_names=core_registry().names(),
        skill_names=catalog.names(),
    ).classify(TaskInput(text="choose the relevant skill"))

    assert set(calls["json"]["questions"]["skill"]["criteria"]) == {
        "none",
        "safe-change-protocol",
        "qa-validation",
    }


def test_http_jev_rejects_skill_outside_catalog(monkeypatch) -> None:
    catalog = SkillCatalog.from_skills([
        SkillMetadata(name="safe-change-protocol", description="safe changes"),
    ])
    response = _jev_response(skill="safe-change-protocol")
    response["answers"]["skill"]["choice"] = "invented-skill"
    monkeypatch.setenv("TYPESAFE_API_KEY", _test_credential())
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: _response(payload=response))

    result = route_task(
        TaskInput(text="fix the backend API validation"),
        jev=HttpJevClassifier(
            agent_names=core_registry().names(),
            skill_names=catalog.names(),
        ),
        registry=core_registry(),
        skills=catalog,
    )

    assert result.source == "fallback"
    assert result.fallback_reason == "jev_schema_error"


def test_subprocess_jev_accepts_legacy_route_without_decision_evidence() -> None:
    legacy_payload = json.dumps({
        "task_type": "implementation",
        "domains": ["backend"],
        "risk": "medium",
        "agents": ["software-engineer"],
        "skills": [],
        "workflow": "implementation",
        "confidence": 0.95,
    })
    classifier = SubprocessJevClassifier([
        sys.executable,
        "-c",
        "import sys; print(sys.argv[1])",
        legacy_payload,
    ])

    result = route_task(
        TaskInput(text="fix the backend API validation"),
        jev=classifier,
        registry=core_registry(),
        skills=empty_catalog(),
    )

    assert result.source == "jev"
    assert result.agents == ["software-engineer"]


def test_runtime_factory_uses_http_jev_when_api_key_exists(monkeypatch) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", _test_credential())
    controller = CodexHookController.__new__(CodexHookController)

    classifier = controller._jev(agent_names=core_registry().names())

    assert isinstance(classifier, HttpJevClassifier)


def test_typesafe_api_key_never_leaks_to_errors_output_or_receipts(tmp_path, monkeypatch, capsys) -> None:
    credential = _test_credential()
    monkeypatch.setenv("TYPESAFE_API_KEY", credential)

    def failure(*args, **kwargs):
        request = httpx.Request("POST", "https://api.typesafe.ai/v1/systemone")
        raise httpx.ConnectError(credential, request=request)

    monkeypatch.setattr(httpx, "post", failure)
    classifier = HttpJevClassifier(agent_names=core_registry().names())
    with pytest.raises(RoutingError) as error:
        classifier.classify(TaskInput(text="fix the backend API validation"))
    assert credential not in str(error.value)

    result = route_task(
        TaskInput(text="fix the backend API validation"),
        jev=classifier,
        registry=core_registry(),
        skills=empty_catalog(),
    )
    output = json.dumps(result.model_dump(mode="json"))
    captured = capsys.readouterr()
    assert credential not in output
    assert credential not in captured.out
    assert credential not in captured.err
    assert result.fallback_reason == "jev_http_error"

    receipt = ReceiptWriter(tmp_path).write(
        ReceiptData(
            execution_id="exec_secret_check",
            objective="fix the backend API validation",
            agents=result.agents,
            status="COMPLETED",
        )
    )
    assert credential not in receipt.read_text(encoding="utf-8")
