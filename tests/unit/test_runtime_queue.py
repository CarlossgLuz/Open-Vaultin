from pathlib import Path

from vaultin.runtime.queue import SyncQueue, SyncQueueItem


def test_queue_deduplicates_by_execution_repository_and_sha(tmp_path: Path) -> None:
    queue = SyncQueue(tmp_path / "sync-queue.jsonl")
    item = SyncQueueItem(
        execution_id="exec_1",
        repository="acme/Vaultin",
        local_sha="abc123",
        state="PENDING_SYNC",
    )
    assert queue.enqueue(item) is True
    assert queue.enqueue(item) is False
    assert queue.pending() == [item]


def test_queue_survives_new_instance(tmp_path: Path) -> None:
    path = tmp_path / "sync-queue.jsonl"
    first = SyncQueue(path)
    item = SyncQueueItem(
        execution_id="exec_2",
        repository="acme/vault-demo",
        local_sha="def456",
        state="PARTIAL_SYNC",
    )
    first.enqueue(item)
    second = SyncQueue(path)
    assert second.pending() == [item]
