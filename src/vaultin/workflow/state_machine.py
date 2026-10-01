from collections import deque
from pathlib import Path

import yaml

from vaultin.errors import ConfigError
from vaultin.models import ExecutionState


class StateMachine:
    def __init__(self, transitions: dict[ExecutionState, set[ExecutionState]], terminal: set[ExecutionState]) -> None:
        self.transitions = transitions
        self.terminal = terminal

    @classmethod
    def default(cls, root: Path | None = None) -> "StateMachine":
        base = root or Path.cwd()
        path = base / "workflows" / "state-machine.yaml"
        if not path.is_file():
            raise ConfigError("workflows/state-machine.yaml not found")
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            terminal = {ExecutionState(value) for value in data.get("terminal_states", [])}
            transitions = {
                ExecutionState(source): {ExecutionState(target) for target in targets}
                for source, targets in (data.get("transitions", {}) or {}).items()
            }
        except (yaml.YAMLError, ValueError, TypeError) as exc:
            raise ConfigError(f"invalid workflow state machine: {exc}") from exc

        declared = set(ExecutionState)
        if set(transitions) != declared:
            missing = declared - set(transitions)
            extra = set(transitions) - declared
            raise ConfigError(f"state machine declaration mismatch: missing={missing}, extra={extra}")
        machine = cls(transitions, terminal)
        without_exit = machine.states_without_exit_path()
        if without_exit:
            raise ConfigError(f"states without terminal path: {sorted(state.value for state in without_exit)}")
        return machine

    def can_transition(self, current: ExecutionState, target: ExecutionState) -> bool:
        return target in self.transitions.get(current, set())

    def transition(self, current: ExecutionState, target: ExecutionState) -> ExecutionState:
        if not self.can_transition(current, target):
            raise ValueError(f"invalid transition {current.value} -> {target.value}")
        return target

    def _has_terminal_path(self, start: ExecutionState) -> bool:
        if start in self.terminal:
            return True
        seen = {start}
        queue = deque([start])
        while queue:
            state = queue.popleft()
            for nxt in self.transitions.get(state, set()):
                if nxt in self.terminal:
                    return True
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return False

    def states_without_exit_path(self) -> set[ExecutionState]:
        return {state for state in ExecutionState if state not in self.terminal and not self._has_terminal_path(state)}
