from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

import yaml

from vaultin.agents.registry import AgentRegistry
from vaultin.config import load_settings
from vaultin.errors import GovernanceBlocked
from vaultin.git.repo import GitRepo
from vaultin.hooks.session_state import CodexSessionState, CodexSessionStore, WorkspaceTracker
from vaultin.knowledge.curator import KnowledgeCurator
from vaultin.ledger.store import LedgerStore
from vaultin.models import ActionContext, ExecutionState, PolicyDecisionKind
from vaultin.orchestrator import ExecutionContext, Orchestrator, TaskRequest
from vaultin.paths import VaultinPaths
from vaultin.policy.engine import PolicyEngine
from vaultin.projects.discovery import ProjectDiscovery
from vaultin.routing.jev import HttpJevClassifier, RouteProposal, RoutingError
from vaultin.runtime.health import HealthChecker
from vaultin.runtime.queue import SyncQueue, SyncQueueItem
from vaultin.skills.catalog import SkillCatalog
from vaultin.workflow.state_machine import StateMachine


def _policy_candidates(payload: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    explicit = payload.get("action")
    if isinstance(explicit, str) and explicit.strip():
        candidates.append(explicit.strip().casefold())

    tool_name = payload.get("tool_name")
    if isinstance(tool_name, str) and tool_name.strip():
        candidates.append(tool_name.strip().casefold())

    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        command = tool_input.get("command")
        if isinstance(command, str):
            for token in re.findall(r"[A-Za-z0-9_.:-]+", command):
                normalized = token.casefold()
                candidates.append(normalized)
                candidates.append(normalized.replace("-", "_"))
        description = tool_input.get("description")
        if isinstance(description, str):
            for token in re.findall(r"[A-Za-z0-9_.:-]+", description):
                candidates.append(token.casefold().replace("-", "_"))

    result: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result or ["tool"]


class HookRuntime:
    """Small policy-only runtime kept for direct hook contract tests."""

    def __init__(self, *, root: Path, policy_engine: PolicyEngine) -> None:
        self.root = Path(root)
        self.policy_engine = policy_engine

    def handle(self, *, event: str, payload: dict) -> dict:
        if event == "pre-tool":
            for action in _policy_candidates(payload):
                decision = self.policy_engine.evaluate(
                    ActionContext(action=action, user_authorized=True, project_policy={})
                )
                if decision.kind is PolicyDecisionKind.DENY:
                    return {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": decision.reason,
                        }
                    }
            return {}
        if event == "session-start":
            return {
                "continue": True,
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": (
                        f"Vaultin is active. Canonical root: {self.root}. "
                        "Route work through Vaultin governance and derive final claims from execution evidence."
                    ),
                },
            }
        if event == "prompt-submit":
            return {
                "continue": True,
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": "Classify and route this turn through the Vaultin orchestrator before mutation.",
                },
            }
        if event == "post-tool":
            return {"systemMessage": "Vaultin observed the completed local tool operation."}
        if event == "stop":
            return {
                "continue": True,
                "systemMessage": "Finalize Vaultin ledger, receipt, and synchronization before claiming completion.",
            }
        if event == "session-end":
            return {}
        raise ValueError(f"unsupported hook event: {event}")


class _FallbackJev:
    def classify(self, task):
        raise RoutingError("JEV command is not configured; deterministic fallback required")


class CodexHookController:
    """Persistent Codex lifecycle controller backed by Vaultin's durable ledger."""

    def __init__(
        self,
        *,
        root: Path,
        publish_receipts: bool | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.settings = load_settings(self.root)
        self.publish_receipts = (
            os.environ.get("VAULTIN_PUBLISH_RECEIPTS", "").casefold() in {"1", "true", "yes", "on"}
            if publish_receipts is None
            else publish_receipts
        )
        self.paths = VaultinPaths.from_root(self.root)
        self.ledger = LedgerStore(self.paths.ledger_db)
        self.policy_engine = load_policy(self.root)
        self.session_store = CodexSessionStore(self.paths.runtime / "codex-sessions")
        self.workspace_tracker = WorkspaceTracker()

    def _jev(self, *, agent_names: list[str], skill_names: list[str] | None = None):
        try:
            if not os.environ["TYPESAFE_API_KEY"]:
                return _FallbackJev()
        except KeyError:
            return _FallbackJev()

        # JEV owns routing so Codex receives only the compact route. Keep the
        # classifier inside the prompt-hook budget instead of letting a slow
        # network call stall the whole turn.
        raw_timeout = os.environ.get("VAULTIN_JEV_TIMEOUT_SECONDS", "3")
        try:
            timeout = float(raw_timeout)
        except ValueError:
            timeout = 3.0
        timeout = min(max(timeout, 0.5), 5.0)
        return HttpJevClassifier(
            agent_names=agent_names,
            skill_names=skill_names or (),
            timeout_seconds=timeout,
        )

    def _orchestrator(self) -> Orchestrator:
        registry = AgentRegistry.load(self.root)
        skills = SkillCatalog.load(self.root)
        return Orchestrator(
            root=self.root,
            ledger=self.ledger,
            policy_engine=self.policy_engine,
            state_machine=StateMachine.default(self.root),
            registry=registry,
            skills=skills,
            jev=self._jev(agent_names=registry.names(), skill_names=skills.names()),
            curator=KnowledgeCurator(),
        )

    @staticmethod
    def _required(payload: dict[str, Any], field: str) -> str:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise GovernanceBlocked(f"Codex hook payload missing required field: {field}")
        return value.strip()

    @staticmethod
    def _route_context(execution_id: str, route: RouteProposal) -> dict[str, Any]:
        agents = ",".join(route.agents)
        skills = ",".join(route.skills) or "none"
        return {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": (
                    f"Vaultin execution_id={execution_id}; wf={route.workflow}; "
                    f"agent={agents}; skills={skills}. Use this route."
                ),
            },
        }

    def _recover_active_execution(self, state: CodexSessionState, *, reason: str) -> None:
        execution_id = state.execution_id
        if not execution_id:
            return
        try:
            record = self.ledger.execution(execution_id)
        except (KeyError, ValueError):
            self._clear_execution_context(state)
            return

        if record.finished_at is None:
            current = ExecutionState(record.status)
            final_status = current
            terminal = {
                ExecutionState.COMPLETED,
                ExecutionState.BLOCKED,
                ExecutionState.FAILED,
                ExecutionState.ROLLED_BACK,
            }
            if current not in terminal:
                machine = StateMachine.default(self.root)
                if machine.can_transition(current, ExecutionState.FAILED):
                    self.ledger.record_event(
                        execution_id,
                        ExecutionState.FAILED.value,
                        {"reason": reason, "recovered": True},
                    )
                else:
                    self.ledger.record_observation(
                        execution_id,
                        "RECOVERY_FORCED",
                        {"reason": reason, "from_state": current.value},
                    )
                final_status = ExecutionState.FAILED
            self.ledger.finish_execution(execution_id, status=final_status.value)

        self._clear_execution_context(state)

    def _restore(self, state: CodexSessionState) -> Orchestrator:
        if not state.execution_id or not state.request or not state.route:
            raise GovernanceBlocked("Vaultin execution context unavailable")
        orchestrator = self._orchestrator()
        context = ExecutionContext(
            execution_id=state.execution_id,
            request=TaskRequest.model_validate(state.request),
            route=RouteProposal.model_validate(state.route),
            state=ExecutionState(self.ledger.execution(state.execution_id).status),
        )
        orchestrator.restore_context(context)
        return orchestrator

    def _session_start(self, payload: dict[str, Any]) -> dict:
        session_id = self._required(payload, "session_id")
        report = HealthChecker(self.root).run()
        if report.status != "PASS":
            blocked = "; ".join(
                f"{item.name}: {item.detail}" for item in report.checks if item.status != "PASS"
            )
            return {
                "continue": False,
                "stopReason": f"Vaultin health is BLOCKED: {blocked}",
                "systemMessage": "Vaultin blocked this Codex turn because governance health failed.",
            }
        with self.session_store.transaction_lock(session_id, timeout=1):
            state = self.session_store.load(session_id)
            if state is None:
                self.session_store.save(CodexSessionState(session_id=session_id))
            elif state.execution_id:
                self._recover_active_execution(
                    state,
                    reason="new SessionStart superseded an inherited active execution",
                )
        return {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "Vaultin active. Use governed routing and evidence-backed finalization.",
            },
        }

    def _prompt_submit(self, payload: dict[str, Any]) -> dict:
        session_id = self._required(payload, "session_id")
        turn_id = self._required(payload, "turn_id")
        prompt = self._required(payload, "prompt")
        cwd = Path(self._required(payload, "cwd")).resolve()

        with self.session_store.transaction_lock(session_id):
            state = self.session_store.load(session_id) or CodexSessionState(session_id=session_id)

            if state.execution_id:
                try:
                    record = self.ledger.execution(state.execution_id)
                except (KeyError, ValueError):
                    self._recover_active_execution(
                        state,
                        reason="execution ledger unavailable during prompt recovery",
                    )
                else:
                    if record.finished_at is not None:
                        self._clear_execution_context(state)
                    elif state.turn_id == turn_id and state.request and state.route:
                        # Codex may deliver the same turn hook more than once. Reuse
                        # the durable execution instead of allocating a duplicate.
                        return self._route_context(
                            state.execution_id,
                            RouteProposal.model_validate(state.route),
                        )
                    else:
                        # A previous turn reached the next UserPromptSubmit without
                        # Stop/Interrupt finalization. Fail that orphan visibly and
                        # release the session instead of blocking the new prompt.
                        self._recover_active_execution(
                            state,
                            reason=(
                                f"superseded by turn {turn_id}; previous turn "
                                "did not finalize through Stop/Interrupt"
                            ),
                        )

            project = ProjectDiscovery().detect(cwd)
            request = TaskRequest(
                client="codex",
                text=prompt,
                cwd=str(cwd),
                user_authorized=True,
                project=project.slug if project else None,
            )
            orchestrator = self._orchestrator()
            context = orchestrator.start(request)
            orchestrator.mark_execution_started(context.execution_id)

            state = CodexSessionState(
                session_id=session_id,
                turn_id=turn_id,
                execution_id=context.execution_id,
                request=request.model_dump(mode="json"),
                route=context.route.model_dump(mode="json"),
                workspace=self.workspace_tracker.snapshot(cwd),
            )
            self.session_store.save(state)

        return self._route_context(context.execution_id, context.route)

    def _pre_tool(self, payload: dict[str, Any]) -> dict:
        # PreToolUse policy evaluation is intentionally stateless. Codex may invoke
        # a tool before UserPromptSubmit has persisted an execution context, or a
        # previous hook process may have lost/recovered that context. Blocking here
        # creates a bootstrap deadlock because even safe reads/Git discovery cannot
        # run to restore the session. Policy remains authoritative: explicit denies
        # and policy-engine failures are still denied below.
        self._required(payload, "session_id")
        try:
            for action in _policy_candidates(payload):
                decision = self.policy_engine.evaluate(
                    ActionContext(action=action, user_authorized=True)
                )
                if decision.kind is PolicyDecisionKind.DENY:
                    return {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": decision.reason,
                        }
                    }
        except Exception as exc:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"Vaultin policy validation unavailable: {exc}",
                }
            }

        return {}

    def _post_tool(self, payload: dict[str, Any]) -> dict:
        session_id = self._required(payload, "session_id")
        state = self.session_store.load(session_id)
        if state and state.execution_id:
            self.ledger.record_observation(
                state.execution_id,
                "TOOL_COMPLETED",
                {
                    "tool_name": str(payload.get("tool_name") or "unknown"),
                    "tool_use_id": str(payload.get("tool_use_id") or ""),
                    "response_type": type(payload.get("tool_response")).__name__,
                },
            )
        return {}

    def _project_git_evidence(self, cwd: str) -> dict[str, str]:
        try:
            repo = GitRepo(Path(cwd))
            return {"project": repo.current_sha()}
        except Exception:
            return {}

    def _publish_receipt(self, receipt_path: str, execution_id: str) -> tuple[dict[str, str], list[str]]:
        if not self.publish_receipts:
            return {}, []
        try:
            receipt = Path(receipt_path).resolve()
            relative = receipt.relative_to(self.root).as_posix()
            repo = GitRepo(self.root)
            sha = repo.commit([relative], f"memory: record {execution_id}", force=True)
            SyncQueue(self.paths.queue_jsonl).enqueue(
                SyncQueueItem(
                    execution_id=execution_id,
                    repository=self.settings.repository,
                    local_sha=sha,
                    state=ExecutionState.PENDING_SYNC.value,
                )
            )
            self.ledger.record_observation(
                execution_id,
                "VAULTIN_RECEIPT_QUEUED",
                {"repository": self.settings.repository, "local_sha": sha},
            )
            return {"vaultin": sha}, ["Vaultin receipt publication queued"]
        except Exception as exc:
            self.ledger.record_observation(
                execution_id,
                "VAULTIN_RECEIPT_PUBLISH_FAILED",
                {"error_type": type(exc).__name__},
            )
            return {}, [f"Vaultin receipt publication failed: {type(exc).__name__}"]

    def _record_last_assistant_message(self, execution_id: str, payload: dict[str, Any]) -> None:
        message = payload.get("last_assistant_message")
        observation: dict[str, Any] = {"present": message is not None}
        if isinstance(message, str):
            observation.update(
                {
                    "length": len(message),
                    "sha256": sha256(message.encode("utf-8")).hexdigest(),
                }
            )
        elif message is not None:
            observation["type"] = type(message).__name__
        self.ledger.record_observation(
            execution_id,
            "CODEX_FINAL_RESPONSE_OBSERVED",
            observation,
        )

    def _clear_execution_context(self, state: CodexSessionState, *, receipt_path: str | None = None) -> None:
        state.execution_id = None
        state.turn_id = None
        state.request = None
        state.route = None
        state.workspace = None
        if receipt_path is not None:
            state.receipt_path = receipt_path
        self.session_store.save(state)

    def _stop(self, payload: dict[str, Any]) -> dict:
        session_id = self._required(payload, "session_id")
        turn_id = self._required(payload, "turn_id")

        with self.session_store.transaction_lock(session_id):
            state = self.session_store.load(session_id)
            if state is None or not state.execution_id:
                return {}

            # Ignore a late Stop from an older turn; never finalize a newer turn.
            if state.turn_id and state.turn_id != turn_id:
                return {}

            if payload.get("stop_hook_active") is True:
                self._recover_active_execution(
                    state,
                    reason="Stop continuation re-entry detected",
                )
                return {
                    "systemMessage": "Vaultin recovered a repeated Stop hook and released the session."
                }

            if not state.workspace:
                self._recover_active_execution(
                    state,
                    reason="execution workspace snapshot missing during Stop",
                )
                return {
                    "systemMessage": "Vaultin could not finalize evidence; execution marked FAILED and session released."
                }

            execution_id = state.execution_id
            try:
                record = self.ledger.execution(execution_id)
            except (KeyError, ValueError):
                self._recover_active_execution(
                    state,
                    reason="execution ledger inconsistent during Stop",
                )
                return {
                    "systemMessage": "Vaultin recovered an inconsistent execution and released the session."
                }

            if record.finished_at is not None:
                self._clear_execution_context(state)
                return {}

            self._record_last_assistant_message(execution_id, payload)
            try:
                orchestrator = self._restore(state)
                files_changed = self.workspace_tracker.changed_paths(state.workspace)
                git_evidence = self._project_git_evidence(state.workspace.cwd)
                result = orchestrator.finalize(
                    execution_id,
                    files_changed=files_changed,
                    git=git_evidence,
                )
            except (GovernanceBlocked, KeyError, ValueError) as exc:
                self._recover_active_execution(
                    state,
                    reason=f"Stop finalization failed: {type(exc).__name__}",
                )
                return {
                    "systemMessage": "Vaultin finalization degraded; execution marked FAILED and session released."
                }

            if result.state not in {ExecutionState.COMPLETED, ExecutionState.PENDING_SYNC}:
                self._recover_active_execution(
                    state,
                    reason=f"unexpected Stop terminal state {result.state.value}",
                )
                return {
                    "systemMessage": "Vaultin reached an unexpected state; execution marked FAILED and session released."
                }

            self._publish_receipt(result.receipt_path, execution_id)
            receipt_path = Path(result.receipt_path).relative_to(self.root).as_posix()
            self._clear_execution_context(state, receipt_path=receipt_path)
            return {}

    def _interrupt(self, payload: dict[str, Any]) -> dict:
        session_id = self._required(payload, "session_id")
        turn_id = self._required(payload, "turn_id")
        with self.session_store.transaction_lock(session_id, timeout=1):
            state = self.session_store.load(session_id)
            if state is None or not state.execution_id:
                return {}
            if state.turn_id and state.turn_id != turn_id:
                return {}
            self._recover_active_execution(
                state,
                reason="Codex turn interrupted by user",
            )
        return {}

    def _session_end(self, payload: dict[str, Any]) -> dict:
        session_id = self._required(payload, "session_id")
        with self.session_store.transaction_lock(session_id, timeout=1):
            state = self.session_store.load(session_id)
            if state and state.execution_id:
                self._recover_active_execution(
                    state,
                    reason="Codex session ended before normal finalization",
                )
            self.session_store.delete(session_id)
        return {}

    def handle(self, *, event: str, payload: dict[str, Any]) -> dict:
        if event == "session-start":
            return self._session_start(payload)
        if event == "prompt-submit":
            return self._prompt_submit(payload)
        if event == "pre-tool":
            return self._pre_tool(payload)
        if event == "post-tool":
            return self._post_tool(payload)
        if event == "stop":
            return self._stop(payload)
        if event == "interrupt":
            return self._interrupt(payload)
        if event == "session-end":
            return self._session_end(payload)
        raise ValueError(f"unsupported hook event: {event}")


def resolve_root(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    env = os.environ.get("VAULTIN_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    marker = Path.home() / ".vaultin" / "root"
    if marker.is_file():
        return Path(marker.read_text(encoding="utf-8-sig").strip()).expanduser().resolve()
    raise RuntimeError("Vaultin root is not configured")


def load_policy(root: Path) -> PolicyEngine:
    load_settings(root)
    path = root / "policies" / "core.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise RuntimeError("policies/core.yaml must contain a mapping")
    return PolicyEngine.from_mapping(raw)


def _append_hook_error(event: str, exc: Exception) -> None:
    try:
        log_dir = Path.home() / ".vaultin"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "hook-errors.log").open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "event": event,
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "event",
        choices=["session-start", "prompt-submit", "pre-tool", "post-tool", "stop", "interrupt", "session-end"],
    )
    parser.add_argument("--root", type=Path)
    args = parser.parse_args(argv)
    try:
        payload = json.load(sys.stdin)
        root = resolve_root(args.root)
        response = CodexHookController(root=root).handle(event=args.event, payload=payload)
        json.dump(response, sys.stdout)
        sys.stdout.write("\n")
        return 0
    except Exception as exc:
        _append_hook_error(args.event, exc)
        # Exit code 2 has event-specific control semantics in Codex. In
        # particular, Stop + exit 2 asks the model to continue the turn and can
        # create a loop if finalization itself is failing. Cleanup/telemetry
        # hooks therefore degrade visibly but never steer or reopen the turn.
        if args.event in {"stop", "interrupt", "session-end", "post-tool"}:
            response = (
                {"systemMessage": "Vaultin hook error recorded; lifecycle released without continuation."}
                if args.event == "stop"
                else {}
            )
            json.dump(response, sys.stdout)
            sys.stdout.write("\n")
            return 0
        sys.stderr.write(f"Vaultin hook blocked: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
