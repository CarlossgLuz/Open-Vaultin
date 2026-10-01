from vaultin.workflow.state_machine import StateMachine
from vaultin.models import ExecutionState


def test_partial_sync_has_real_recovery_path() -> None:
    machine = StateMachine.default()
    assert machine.can_transition(ExecutionState.PARTIAL_SYNC, ExecutionState.RETRYING_SYNC)
    assert machine.can_transition(ExecutionState.RETRYING_SYNC, ExecutionState.SYNCING)


def test_all_nonterminal_states_have_exit_paths() -> None:
    machine = StateMachine.default()
    unreachable = machine.states_without_exit_path()
    assert unreachable == set()
