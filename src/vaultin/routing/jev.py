from __future__ import annotations

import json
import logging
import math
import os
import re
import subprocess
from collections.abc import Mapping
from typing import Any, Literal, Protocol, Sequence

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from vaultin.agents.registry import AgentRegistry
from vaultin.skills.catalog import SkillCatalog


logger = logging.getLogger(__name__)

# Retain the existing 0.65 floor for the two decisions that choose the
# execution owner and workflow. Secondary decisions are evidence, not gates.
REQUIRED_DECISION_THRESHOLDS = {
    "primary_agent": 0.65,
    "workflow": 0.65,
}
ADVISORY_CONFIDENCE_THRESHOLD = 0.65

EXPLICIT_WORKFLOWS = frozenset({
    "implementation",
    "security-review",
    "qa",
    "code-review",
    "exploration",
})
_EXPLICIT_WORKFLOW_RE = re.compile(
    r"(?im)^[ \t]*workflow[ \t]*=[ \t]*([A-Za-z][A-Za-z0-9_-]*)[ \t]*$"
)


def _normalize_workflow_name(value: str) -> str:
    return value.strip().casefold().replace("_", "-")


def explicit_workflow(task: "TaskInput") -> str | None:
    """Resolve an explicit workflow directive before JEV or heuristics.

    Prompt directives have highest precedence. Metadata is reserved for
    trusted handoff/runtime context and is considered only when the prompt
    itself does not declare a workflow.
    """
    matches = [_normalize_workflow_name(item) for item in _EXPLICIT_WORKFLOW_RE.findall(task.text)]
    if matches:
        unique = set(matches)
        if len(unique) != 1:
            raise RoutingError(
                "conflicting explicit workflow directives",
                reason="invalid_explicit_workflow",
            )
        workflow = matches[0]
        if workflow not in EXPLICIT_WORKFLOWS:
            raise RoutingError(
                "unsupported explicit workflow directive",
                reason="invalid_explicit_workflow",
            )
        return workflow

    metadata_workflow = task.metadata.get("workflow")
    if metadata_workflow is None:
        return None
    if not isinstance(metadata_workflow, str):
        raise RoutingError(
            "invalid workflow handoff metadata",
            reason="invalid_explicit_workflow",
        )
    workflow = _normalize_workflow_name(metadata_workflow)
    if workflow not in EXPLICIT_WORKFLOWS:
        raise RoutingError(
            "unsupported workflow handoff metadata",
            reason="invalid_explicit_workflow",
        )
    return workflow


def _registered_agent(registry: AgentRegistry, *preferred: str) -> str:
    registered = set(registry.names())
    for name in preferred:
        if name in registered:
            return name
    raise RoutingError(
        "explicit workflow has no registered execution agent",
        reason="invalid_route",
    )


def _explicit_route(task: "TaskInput", workflow: str, *, registry: AgentRegistry) -> "RouteProposal":
    text = task.text.casefold()

    if workflow == "implementation":
        if re.search(r"\b(frontend|react|next\.js|css|ui|interface)\b", text):
            agent = _registered_agent(registry, "frontend-engineer", "software-engineer")
            domain = "frontend"
        elif re.search(r"\b(infra|infrastructure|docker|kubernetes|k8s|terraform|linux|server|network)\b", text):
            agent = _registered_agent(registry, "platform-engineer", "software-engineer")
            domain = "platform"
        elif re.search(r"\b(test|tests|qa|quality)\b", text):
            agent = _registered_agent(registry, "qa-engineer", "software-engineer")
            domain = "qa"
        else:
            agent = _registered_agent(registry, "software-engineer", "frontend-engineer")
            domain = "software"
        return RouteProposal(
            task_type="implementation",
            domains=[domain],
            risk="medium",
            agents=[agent],
            skills=[],
            workflow="implementation",
            confidence=1.0,
            source="explicit",
            decision_confidences={"workflow": 1.0, "primary_agent": 1.0},
        )

    mapping = {
        "security-review": ("security-review", "security", "high", "security-reviewer"),
        "qa": ("qa", "qa", "medium", "qa-engineer"),
        "code-review": ("code-review", "engineering", "medium", "code-reviewer"),
        "exploration": ("exploration", "unknown", "low", "explorer"),
    }
    task_type, domain, risk, agent_name = mapping[workflow]
    return RouteProposal(
        task_type=task_type,
        domains=[domain],
        risk=risk,
        agents=[_registered_agent(registry, agent_name)],
        skills=[],
        workflow=workflow,
        confidence=1.0,
        source="explicit",
        decision_confidences={"workflow": 1.0, "primary_agent": 1.0},
    )


class RoutingError(RuntimeError):
    def __init__(self, message: str, *, reason: str = "jev_error") -> None:
        super().__init__(message)
        self.reason = reason


class TaskInput(BaseModel):
    text: str
    cwd: str | None = None
    current_project: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RouteProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: str
    domains: list[str]
    risk: Literal["low", "medium", "high", "critical"]
    agents: list[str]
    skills: list[str]
    workflow: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: Literal["jev", "fallback", "explicit"] = "jev"
    decision_confidences: dict[str, float] = Field(default_factory=dict)
    decision_probabilities: dict[str, dict[str, float]] = Field(default_factory=dict)
    uncertain_decisions: list[str] = Field(default_factory=list)
    fallback_reason: str | None = None


class JevClassifier(Protocol):
    def classify(self, task: TaskInput) -> RouteProposal: ...


class HttpJevClassifier:
    """Advisory TypeSafe/JEV classifier using the official System One API."""

    endpoint = "https://api.typesafe.ai/v1/systemone"
    model = "jev-latest"
    _task_types = ("implementation", "security-review", "qa", "code-review", "exploration")
    _domains = ("backend", "frontend", "security", "qa", "platform", "release", "knowledge", "unknown")
    _risks = ("low", "medium", "high", "critical")
    _workflows = ("implementation", "security-review", "qa", "code-review", "exploration")

    def __init__(
        self,
        *,
        agent_names: Sequence[str],
        skill_names: Sequence[str] = (),
        timeout_seconds: float = 5.0,
    ) -> None:
        names = tuple(sorted(set(agent_names)))
        if not names:
            raise ValueError("JEV agent list must not be empty")
        skills = tuple(sorted(set(skill_names)))
        if "none" in skills:
            raise ValueError("JEV skill name 'none' is reserved")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("JEV timeout must be finite and positive")
        self.agent_names = names
        self.skill_names = skills
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _question(instructions: str, options: Sequence[str]) -> dict[str, Any]:
        return {
            "type": "choice",
            "instructions": instructions,
            "criteria": {option: f"Registered Vaultin option: {option}" for option in options},
        }

    @staticmethod
    def _skill_question(options: Sequence[str]) -> dict[str, Any]:
        return {
            "type": "choice",
            "instructions": "Choose the most relevant registered Vaultin skill, or none.",
            "criteria": {
                option: "No additional skill is needed."
                if option == "none"
                else f"Registered Vaultin skill: {option}"
                for option in options
            },
        }

    def _payload(self, task: TaskInput) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "state": {
                "task": task.text,
                "cwd": task.cwd,
                "current_project": task.current_project,
            },
            "model": self.model,
            "questions": {
                "task_type": self._question("Classify the primary task type.", self._task_types),
                "domain": self._question("Classify the primary technical domain.", self._domains),
                "primary_agent": self._question(
                    "Choose the registered agent that owns the primary artifact or domain.",
                    self.agent_names,
                ),
                "risk": self._question("Classify the operational risk.", self._risks),
                "workflow": self._question("Choose the registered workflow for this task.", self._workflows),
            },
        }
        if self.skill_names:
            payload["questions"]["skill"] = self._skill_question(("none", *self.skill_names))
        return payload

    @staticmethod
    def _validate_choice_answer(
        answer: object,
        *,
        options: Sequence[str],
    ) -> tuple[str, float, dict[str, float]]:
        if not isinstance(answer, dict):
            raise ValueError("choice answer must be an object")
        if answer.get("type") != "choice":
            raise ValueError("choice answer has an invalid type")
        choice = answer.get("choice")
        probabilities = answer.get("probabilities")
        confidence = answer.get("confidence")
        if not isinstance(choice, str) or choice not in options:
            raise ValueError("choice answer is not registered")
        if not isinstance(probabilities, dict) or set(probabilities) != set(options):
            raise ValueError("choice probabilities do not match the question")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0 <= value <= 1
            for value in probabilities.values()
        ):
            raise ValueError("choice probabilities are invalid")
        if abs(sum(probabilities.values()) - 1.0) > 0.02:
            raise ValueError("choice probabilities do not sum to one")
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not math.isfinite(confidence)
            or not 0 <= confidence <= 1
        ):
            raise ValueError("choice confidence is invalid")
        return choice, float(confidence), {key: float(value) for key, value in probabilities.items()}

    def _route_from_response(self, payload: object) -> RouteProposal:
        if not isinstance(payload, dict) or not isinstance(payload.get("model"), str):
            raise ValueError("JEV response model is invalid")
        answers = payload.get("answers")
        usage = payload.get("usage")
        expected_usage = {"input_tokens", "output_tokens"}
        expected_answers = {"task_type", "domain", "primary_agent", "risk", "workflow"}
        if self.skill_names:
            expected_answers.add("skill")
        if not isinstance(answers, dict) or set(answers) != expected_answers:
            raise ValueError("JEV response answers are invalid")
        if not isinstance(usage, dict) or set(usage) != expected_usage:
            raise ValueError("JEV response usage is invalid")
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in usage.values()
        ):
            raise ValueError("JEV response usage is invalid")

        task_type, task_confidence, task_probabilities = self._validate_choice_answer(
            answers["task_type"], options=self._task_types
        )
        domain, domain_confidence, domain_probabilities = self._validate_choice_answer(
            answers["domain"], options=self._domains
        )
        primary_agent, agent_confidence, agent_probabilities = self._validate_choice_answer(
            answers["primary_agent"], options=self.agent_names
        )
        risk, risk_confidence, risk_probabilities = self._validate_choice_answer(
            answers["risk"], options=self._risks
        )
        workflow, workflow_confidence, workflow_probabilities = self._validate_choice_answer(
            answers["workflow"], options=self._workflows
        )
        decision_confidences = {
            "task_type": task_confidence,
            "domain": domain_confidence,
            "primary_agent": agent_confidence,
            "risk": risk_confidence,
            "workflow": workflow_confidence,
        }
        decision_probabilities = {
            "task_type": task_probabilities,
            "domain": domain_probabilities,
            "primary_agent": agent_probabilities,
            "risk": risk_probabilities,
            "workflow": workflow_probabilities,
        }
        skills: list[str] = []
        if self.skill_names:
            skill, skill_confidence, skill_probabilities = self._validate_choice_answer(
                answers["skill"], options=("none", *self.skill_names)
            )
            decision_confidences["skill"] = skill_confidence
            decision_probabilities["skill"] = skill_probabilities
            if skill != "none" and skill_confidence >= ADVISORY_CONFIDENCE_THRESHOLD:
                skills.append(skill)
        return RouteProposal(
            task_type=task_type,
            domains=[domain],
            risk=risk,
            agents=[primary_agent],
            skills=skills,
            workflow=workflow,
            # Backward-compatible scalar: only routing-critical decisions are
            # reflected here. Selection itself uses decision_confidences below.
            confidence=min(agent_confidence, workflow_confidence),
            decision_confidences=decision_confidences,
            decision_probabilities=decision_probabilities,
            uncertain_decisions=sorted(
                name
                for name, value in decision_confidences.items()
                if value < ADVISORY_CONFIDENCE_THRESHOLD
            ),
        )

    def classify(self, task: TaskInput) -> RouteProposal:
        try:
            api_key = os.environ["TYPESAFE_API_KEY"]
        except KeyError:
            raise RoutingError("JEV API key is unavailable", reason="missing_api_key") from None
        if not api_key:
            raise RoutingError("JEV API key is unavailable", reason="missing_api_key")

        try:
            response = httpx.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=self._payload(task),
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException:
            raise RoutingError("JEV request timed out", reason="jev_http_error") from None
        except httpx.HTTPError:
            raise RoutingError("JEV HTTP request failed", reason="jev_http_error") from None
        except (TypeError, ValueError):
            raise RoutingError("invalid JEV JSON response", reason="jev_schema_error") from None

        try:
            return self._route_from_response(payload)
        except (TypeError, ValueError, ValidationError):
            raise RoutingError("invalid JEV response schema", reason="jev_schema_error") from None


class SubprocessJevClassifier:
    def __init__(self, command: Sequence[str], *, timeout_seconds: float = 5.0) -> None:
        if not command:
            raise ValueError("JEV command must not be empty")
        self.command = list(command)
        self.timeout_seconds = timeout_seconds

    def classify(self, task: TaskInput) -> RouteProposal:
        try:
            result = subprocess.run(
                self.command,
                input=task.model_dump_json(),
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                shell=False,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise RoutingError("JEV execution failed", reason="jev_execution_error") from None
        if result.returncode != 0:
            raise RoutingError("JEV process failed", reason="jev_execution_error")
        try:
            payload = json.loads(result.stdout)
            return RouteProposal.model_validate(payload)
        except (json.JSONDecodeError, ValidationError):
            raise RoutingError("invalid JEV output", reason="jev_schema_error") from None


def validate_route(proposal: RouteProposal, *, registry: AgentRegistry, skills: SkillCatalog) -> RouteProposal:
    if not proposal.agents:
        raise RoutingError("route must contain at least one agent", reason="invalid_route")
    registered_agents = set(registry.names())
    for agent in proposal.agents:
        if agent not in registered_agents:
            raise RoutingError("route contains an unregistered agent", reason="unregistered_agent")
    registered_skills = set(skills.names())
    for skill in proposal.skills:
        if skill not in registered_skills:
            raise RoutingError("route contains an unregistered skill", reason="unregistered_skill")
    if not proposal.workflow.strip():
        raise RoutingError("route workflow must not be empty", reason="invalid_route")
    return proposal


def _decision_confidence(proposal: RouteProposal, decision: str) -> float:
    value = proposal.decision_confidences.get(decision, proposal.confidence)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise RoutingError("invalid JEV decision confidence", reason="jev_schema_error")
    return float(value)


def route_task(
    task: TaskInput,
    *,
    jev: JevClassifier,
    registry: AgentRegistry,
    skills: SkillCatalog | None = None,
    confidence_threshold: float | None = None,
    decision_thresholds: Mapping[str, float] | None = None,
) -> RouteProposal:
    catalog = skills or SkillCatalog.from_skills([])

    # Explicit user/runtime directives are authorization inputs, not hints.
    # Resolve them before JEV so the classifier cannot silently replace the
    # requested primary workflow (and so we avoid an unnecessary model call).
    forced_workflow = explicit_workflow(task)
    if forced_workflow is not None:
        return validate_route(
            _explicit_route(task, forced_workflow, registry=registry),
            registry=registry,
            skills=catalog,
        )

    thresholds = dict(REQUIRED_DECISION_THRESHOLDS)
    if confidence_threshold is not None:
        thresholds.update({decision: confidence_threshold for decision in thresholds})
    if decision_thresholds:
        thresholds.update(decision_thresholds)
    if any(
        decision not in REQUIRED_DECISION_THRESHOLDS
        or isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 <= value <= 1
        for decision, value in thresholds.items()
    ):
        raise ValueError("invalid JEV decision threshold")
    try:
        proposal = jev.classify(task)
        if not isinstance(proposal, RouteProposal):
            raise RoutingError("invalid JEV route proposal", reason="jev_schema_error")
        proposal = validate_route(proposal, registry=registry, skills=catalog)
        for decision, threshold in thresholds.items():
            if _decision_confidence(proposal, decision) < threshold:
                reason = "low_agent_confidence" if decision == "primary_agent" else "low_workflow_confidence"
                raise RoutingError("required JEV decision is uncertain", reason=reason)
        return proposal.model_copy(update={"source": "jev"})
    except RoutingError as exc:
        fallback_reason = exc.reason
    except RuntimeError:
        # Keep compatibility with legacy classifiers while never exposing
        # their exception text or any classifier-provided content.
        fallback_reason = "jev_error"
    except (TypeError, ValueError, ValidationError):
        fallback_reason = "jev_schema_error"

    logger.info("JEV fallback selected: reason=%s", fallback_reason)
    # JEV is advisory. Typed classifier/adapter failures fall back
    # deterministically and never broaden policy authority.
    from vaultin.routing.fallback import FallbackRouter

    fallback = FallbackRouter().route(task)
    return validate_route(
        fallback,
        registry=registry,
        skills=catalog,
    ).model_copy(update={"source": "fallback", "fallback_reason": fallback_reason})
