from dataclasses import dataclass
from pathlib import Path

from vaultin.config import load_settings


@dataclass(frozen=True)
class VaultinPaths:
    root: Path
    runtime: Path
    ledger_db: Path
    events_jsonl: Path
    queue_jsonl: Path

    @classmethod
    def from_root(cls, root: Path) -> "VaultinPaths":
        root = Path(root).resolve()
        runtime = root / load_settings(root).runtime_dir_name
        return cls(
            root=root,
            runtime=runtime,
            ledger_db=runtime / "vaultin.db",
            events_jsonl=runtime / "events.jsonl",
            queue_jsonl=runtime / "sync-queue.jsonl",
        )
