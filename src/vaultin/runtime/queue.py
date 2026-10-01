from __future__ import annotations

from pathlib import Path

from filelock import FileLock
from pydantic import BaseModel


class SyncQueueItem(BaseModel):
    execution_id: str
    repository: str
    local_sha: str
    state: str

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.execution_id, self.repository, self.local_sha)


class SyncQueue:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = FileLock(str(self.path) + ".lock")

    def _read_unlocked(self) -> list[SyncQueueItem]:
        if not self.path.exists():
            return []
        items: list[SyncQueueItem] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                items.append(SyncQueueItem.model_validate_json(line))
        return items

    def _write_unlocked(self, items: list[SyncQueueItem]) -> None:
        text = "".join(item.model_dump_json() + "\n" for item in items)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(self.path)

    def enqueue(self, item: SyncQueueItem) -> bool:
        with self._lock:
            items = self._read_unlocked()
            if any(existing.key == item.key for existing in items):
                return False
            items.append(item)
            self._write_unlocked(items)
            return True

    def pending(self) -> list[SyncQueueItem]:
        with self._lock:
            return self._read_unlocked()

    def remove(self, item: SyncQueueItem) -> bool:
        with self._lock:
            items = self._read_unlocked()
            retained = [existing for existing in items if existing.key != item.key]
            if len(retained) == len(items):
                return False
            self._write_unlocked(retained)
            return True

    def replace_state(self, item: SyncQueueItem, state: str) -> SyncQueueItem:
        replacement = item.model_copy(update={"state": state})
        with self._lock:
            items = self._read_unlocked()
            found = False
            updated: list[SyncQueueItem] = []
            for existing in items:
                if existing.key == item.key:
                    updated.append(replacement)
                    found = True
                else:
                    updated.append(existing)
            if not found:
                updated.append(replacement)
            self._write_unlocked(updated)
        return replacement
