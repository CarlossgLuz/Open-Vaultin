from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from vaultin.ledger.store import LedgerStore


def test_execution_ids_are_unique_under_concurrency(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path / "vaultin.db")
    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(lambda _: store.begin_execution(client="codex"), range(50)))
    assert len(ids) == len(set(ids)) == 50


def test_events_are_ordered_per_execution(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path / "vaultin.db")
    execution_id = store.begin_execution(client="codex")
    store.record_event(execution_id, "READY", {"ok": True})
    store.record_event(execution_id, "ROUTED", {"agent": "software-engineer"})
    assert [event.kind for event in store.events(execution_id)] == ["READY", "ROUTED"]


def test_finish_execution_persists_terminal_status(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path / "vaultin.db")
    execution_id = store.begin_execution(client="codex")
    store.finish_execution(execution_id, status="COMPLETED")
    assert store.execution(execution_id).status == "COMPLETED"


def test_ledger_releases_database_handle(tmp_path: Path) -> None:
    database = tmp_path / "vaultin.db"
    store = LedgerStore(database)
    execution_id = store.begin_execution(client="codex")
    store.record_event(execution_id, "READY", {})
    store.events(execution_id)
    store.execution(execution_id)
    store.finish_execution(execution_id, status="COMPLETED")
    database.unlink()
    assert not database.exists()
