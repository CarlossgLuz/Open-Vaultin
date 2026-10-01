from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from vaultin.agents.registry import AgentRegistry
from vaultin.errors import GovernanceBlocked
from vaultin.knowledge.curator import KnowledgeCurator
from vaultin.ledger.receipt import ReceiptData, ReceiptWriter
from vaultin.ledger.store import LedgerStore
from vaultin.models import ActionContext, ExecutionState, PolicyDecisionKind
from vaultin.policy.engine import PolicyEngine
from vaultin.routing.jev import JevClassifier, RouteProposal, TaskInput, route_task
from vaultin.skills.catalog import SkillCatalog
from vaultin.workflow.state_machine import StateMachine


class TaskRequest(BaseModel):
    client: str
    text: str
    cwd: str
    user_authorized: bool = False
    project: str | None = None
    project_policy: dict[str, Any] = Field(default_factory=dict)
    project_instructions: dict[str, Any] = Field(default_factory=dict)


class ExecutionContext(BaseModel):
    execution_id: str
    request: TaskRequest
    route: RouteProposal
    state: ExecutionState


class FinalizationResult(BaseModel):
    execution_id: str
    state: ExecutionState
    files_changed: list[str]
    validations: list[str]
    git: dict[str, str] = Field(default_factory=dict)
    pending: list[str] = Field(default_factory=list)
    receipt_path: str
    final_response: str


class Orchestrator:
    def __init__(
        self,
        *,
        root: Path,
        ledger: LedgerStore,
        policy_engine: PolicyEngine,
        state_machine: StateMachine,
        registry: AgentRegistry,
        skills: SkillCatalog,
        jev: JevClassifier,
        curator: KnowledgeCurator,
    ) -> None:
        self.root = Path(root)
        self.ledger = ledger
        self.policy_engine = policy_engine
        self.state_machine = state_machine
        self.registry = registry
        self.skills = skills
        self.jev = jev
        self.curator = curator
        self._contexts: dict[str, ExecutionContext] = {}
        self._validations: dict[str, list[str]] = {}

    def restore_context(
        self,
        context: ExecutionContext,
        *,
        validations: list[str] | None = None,
    ) -> None:
        """Reattach durable execution context across independent hook processes."""
        self._contexts[context.execution_id] = context
        self._validations[context.execution_id] = list(validations or [])

    def _record_transition(self, execution_id: str, target: ExecutionState, payload: dict[str, Any] | None = None) -> None:
        current = ExecutionState(self.ledger.execution(execution_id).status)
        if current == target:
            return
        self.state_machine.transition(current, target)
        self.ledger.record_event(execution_id, target.value, payload or {})

    def _block(self, execution_id: str, reason: str) -> None:
        current = ExecutionState(self.ledger.execution(execution_id).status)
        if current != ExecutionState.BLOCKED and self.state_machine.can_transition(current, ExecutionState.BLOCKED):
            self.ledger.record_event(execution_id, ExecutionState.BLOCKED.value, {"reason": reason})
        self.ledger.finish_execution(execution_id, status=ExecutionState.BLOCKED.value)

    def _validate_governance(self, request: TaskRequest) -> None:
        try:
            decision = self.policy_engine.evaluate(
                ActionContext(
                    action="governance_bootstrap",
                    user_authorized=True,
                    project_policy=request.project_policy,
                    project_instructions=request.project_instructions,
                )
            )
        except Exception as exc:
            raise GovernanceBlocked(f"policy validation unavailable: {exc}") from exc
        if decision.kind is PolicyDecisionKind.DENY:
            raise GovernanceBlocked(decision.reason)

    def start(self, request: TaskRequest) -> ExecutionContext:
        execution_id = self.ledger.begin_execution(client=request.client)
        self.ledger.record_event(execution_id, ExecutionState.INITIALIZING.value, {"cwd": request.cwd})
        try:
            self._validate_governance(request)
            self._record_transition(execution_id, ExecutionState.READY)
            route = route_task(
                TaskInput(text=request.text, cwd=request.cwd, current_project=request.project),
                jev=self.jev,
                registry=self.registry,
                skills=self.skills,
            )
            self._record_transition(execution_id, ExecutionState.ROUTED, route.model_dump(mode="json"))
        except GovernanceBlocked as exc:
            self._block(execution_id, str(exc))
            raise
        except Exception as exc:
            self._block(execution_id, f"routing unavailable: {exc}")
            raise GovernanceBlocked(f"routing unavailable: {exc}") from exc

        context = ExecutionContext(
            execution_id=execution_id,
            request=request,
            route=route,
            state=ExecutionState.ROUTED,
        )
        self._contexts[execution_id] = context
        self._validations[execution_id] = []
        return context

    def mark_execution_started(self, execution_id: str) -> None:
        self._record_transition(execution_id, ExecutionState.EXECUTING)
        if execution_id in self._contexts:
            self._contexts[execution_id].state = ExecutionState.EXECUTING

    def mark_validation(self, execution_id: str, name: str, result: str) -> None:
        current = ExecutionState(self.ledger.execution(execution_id).status)
        if current == ExecutionState.EXECUTING:
            self._record_transition(
                execution_id,
                ExecutionState.VALIDATING,
                {"name": name, "result": result},
            )
        elif current != ExecutionState.VALIDATING:
            raise GovernanceBlocked(f"cannot record validation from state {current.value}")
        self._validations.setdefault(execution_id, []).append(f"{name}: {result}")
        if execution_id in self._contexts:
            self._contexts[execution_id].state = ExecutionState.VALIDATING

    def authorize_tool(self, execution_id: str, *, action: str, user_authorized: bool) -> None:
        context = self._contexts.get(execution_id)
        request = context.request if context else None
        try:
            decision = self.policy_engine.evaluate(
                ActionContext(
                    action=action,
                    user_authorized=user_authorized,
                    project_policy=request.project_policy if request else {},
                    project_instructions=request.project_instructions if request else {},
                )
            )
        except Exception as exc:
            raise GovernanceBlocked(f"policy validation unavailable: {exc}") from exc
        if decision.kind is PolicyDecisionKind.DENY:
            raise GovernanceBlocked(decision.reason)

    @staticmethod
    def _render_final_response(
        *,
        state: ExecutionState,
        files_changed: list[str],
        validations: list[str],
        git: dict[str, str],
        pending: list[str],
        receipt_path: str,
    ) -> str:
        lines = [f"✓ {state.value}", "", "Arquivos alterados:"]
        lines.extend(f"- {path}" for path in (files_changed or ["nenhum arquivo alterado"]))
        lines.extend(["", "Validações:"])
        lines.extend(f"- {item}" for item in (validations or ["nenhuma validação registrada"]))
        lines.extend(["", "Git:"])
        if git:
            lines.extend(f"- {name}: {sha}" for name, sha in sorted(git.items()))
        else:
            lines.append("- n/a")
        lines.extend(["", "Pendências:"])
        lines.extend(f"- {item}" for item in (pending or ["nenhuma"]))
        lines.extend(["", f"Receipt: {receipt_path}"])
        return "\n".join(lines)

    def finalize(
        self,
        execution_id: str,
        *,
        files_changed: list[str],
        git: dict[str, str] | None = None,
        pending: list[str] | None = None,
    ) -> FinalizationResult:
        git_evidence = dict(git or {})
        pending_items = list(pending or [])
        current = ExecutionState(self.ledger.execution(execution_id).status)
        if current == ExecutionState.EXECUTING:
            self._record_transition(execution_id, ExecutionState.VALIDATING, {"automatic": True})
            current = ExecutionState.VALIDATING
        if current != ExecutionState.VALIDATING:
            raise GovernanceBlocked(f"cannot finalize from state {current.value}")

        context = self._contexts.get(execution_id)
        if context is None:
            raise GovernanceBlocked(f"execution context unavailable for {execution_id}")

        validations = list(self._validations.get(execution_id, []))
        final_state = ExecutionState.PENDING_SYNC if pending_items else ExecutionState.COMPLETED

        self._record_transition(execution_id, ExecutionState.CURATING, {"files_changed": files_changed})
        self._record_transition(
            execution_id,
            ExecutionState.COMMITTING,
            {"files_changed": files_changed, "git": git_evidence},
        )

        receipt = ReceiptWriter(self.root).write(
            ReceiptData(
                execution_id=execution_id,
                project=context.request.project,
                objective=context.request.text,
                agents=context.route.agents,
                skills=context.route.skills,
                files_changed=list(files_changed),
                validations=validations,
                git=git_evidence,
                status=final_state.value,
                pending=pending_items,
            )
        )
        try:
            receipt_display = receipt.relative_to(self.root).as_posix()
        except ValueError:
            receipt_display = str(receipt)

        self._record_transition(execution_id, ExecutionState.SYNCING, {"git": git_evidence})
        if pending_items:
            self._record_transition(
                execution_id,
                ExecutionState.PENDING_SYNC,
                {"pending": pending_items},
            )
        else:
            self._record_transition(execution_id, ExecutionState.COMPLETED)
            self.ledger.finish_execution(execution_id, status=ExecutionState.COMPLETED.value)

        context.state = final_state
        final_response = self._render_final_response(
            state=final_state,
            files_changed=list(files_changed),
            validations=validations,
            git=git_evidence,
            pending=pending_items,
            receipt_path=receipt_display,
        )
        return FinalizationResult(
            execution_id=execution_id,
            state=final_state,
            files_changed=list(files_changed),
            validations=validations,
            git=git_evidence,
            pending=pending_items,
            receipt_path=str(receipt),
            final_response=final_response,
        )
