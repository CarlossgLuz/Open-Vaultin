from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import secrets
import sqlite3
from typing import Any

from filelock import FileLock


@dataclass(frozen=True)
class ExecutionRecord:
    execution_id: str
    client: str
    status: str
    started_at: str
    finished_at: str | None


@dataclass(frozen=True)
class LedgerEvent:
    execution_id: str
    sequence: int
    kind: str
    payload: dict[str, Any]
    created_at: str


def _new_execution_id() -> str:
    now = datetime.now(UTC)
    return f"exec_{now:%Y%m%d_%H%M%S}_{secrets.token_hex(4)}"


class LedgerStore:
    def __init__(self, database_path: Path, *, timeout_seconds: float = 5.0) -> None:
        self.timeout_seconds = timeout_seconds
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._schema_lock = FileLock(str(self.database_path) + ".schema.lock", timeout=self.timeout_seconds)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=self.timeout_seconds)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute(f"PRAGMA busy_timeout={int(self.timeout_seconds * 1000)}")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")
            return connection
        except Exception:
            connection.close()
            raise

    def _initialize(self) -> None:
        with self._schema_lock:
            with closing(self._connect()) as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS executions (
                        execution_id TEXT PRIMARY KEY,
                        client TEXT NOT NULL,
                        status TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        finished_at TEXT
                    );
                    CREATE TABLE IF NOT EXISTS events (
                        execution_id TEXT NOT NULL,
                        sequence INTEGER NOT NULL,
                        kind TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        PRIMARY KEY (execution_id, sequence),
                        FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
                    );
                    """
                )
                connection.commit()

    def begin_execution(self, *, client: str) -> str:
        for _ in range(8):
            execution_id = _new_execution_id()
            try:
                with closing(self._connect()) as connection:
                    connection.execute(
                        "INSERT INTO executions(execution_id, client, status, started_at) VALUES (?, ?, ?, ?)",
                        (execution_id, client, "INITIALIZING", datetime.now(UTC).isoformat()),
                    )
                    connection.commit()
                return execution_id
            except sqlite3.IntegrityError:
                continue
        raise RuntimeError("unable to allocate unique execution id")

    def _insert_event(
        self,
        execution_id: str,
        kind: str,
        payload: dict[str, Any] | None,
        *,
        update_status: bool,
    ) -> LedgerEvent:
        encoded = json.dumps(payload or {}, sort_keys=True, ensure_ascii=False)
        created_at = datetime.now(UTC).isoformat()
        with closing(self._connect()) as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT COALESCE(MAX(sequence), 0) + 1 AS next_sequence FROM events WHERE execution_id = ?",
                    (execution_id,),
                ).fetchone()
                if connection.execute(
                    "SELECT 1 FROM executions WHERE execution_id = ?", (execution_id,)
                ).fetchone() is None:
                    raise KeyError(f"unknown execution: {execution_id}")
                sequence = int(row["next_sequence"])
                connection.execute(
                    "INSERT INTO events(execution_id, sequence, kind, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
                    (execution_id, sequence, kind, encoded, created_at),
                )
                if update_status:
                    connection.execute(
                        "UPDATE executions SET status = ? WHERE execution_id = ?",
                        (kind, execution_id),
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return LedgerEvent(execution_id, sequence, kind, payload or {}, created_at)

    def record_event(
        self,
        execution_id: str,
        kind: str,
        payload: dict[str, Any] | None = None,
    ) -> LedgerEvent:
        return self._insert_event(execution_id, kind, payload, update_status=True)

    def record_observation(
        self,
        execution_id: str,
        kind: str,
        payload: dict[str, Any] | None = None,
    ) -> LedgerEvent:
        return self._insert_event(execution_id, kind, payload, update_status=False)

    def events(self, execution_id: str) -> list[LedgerEvent]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT execution_id, sequence, kind, payload_json, created_at "
                "FROM events WHERE execution_id = ? ORDER BY sequence",
                (execution_id,),
            ).fetchall()
        return [
            LedgerEvent(
                execution_id=row["execution_id"],
                sequence=row["sequence"],
                kind=row["kind"],
                payload=json.loads(row["payload_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def finish_execution(self, execution_id: str, *, status: str) -> None:
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                "UPDATE executions SET status = ?, finished_at = ? WHERE execution_id = ?",
                (status, datetime.now(UTC).isoformat(), execution_id),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                raise KeyError(f"unknown execution: {execution_id}")
            connection.commit()

    def execution(self, execution_id: str) -> ExecutionRecord:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT execution_id, client, status, started_at, finished_at FROM executions WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown execution: {execution_id}")
        return ExecutionRecord(
            execution_id=row["execution_id"],
            client=row["client"],
            status=row["status"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
        )
