from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import subprocess
from typing import Any

from filelock import FileLock
from pydantic import BaseModel, Field


class WorkspaceSnapshot(BaseModel):
    cwd: str
    head: str | None = None
    dirty_hashes: dict[str, str | None] = Field(default_factory=dict)


class CodexSessionState(BaseModel):
    session_id: str
    turn_id: str | None = None
    execution_id: str | None = None
    request: dict[str, Any] | None = None
    route: dict[str, Any] | None = None
    workspace: WorkspaceSnapshot | None = None
    receipt_path: str | None = None


class CodexSessionStore:
    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        digest = sha256(session_id.encode("utf-8")).hexdigest()
        return self.directory / f"{digest}.json"

    def _lock(self, session_id: str) -> FileLock:
        return FileLock(str(self._path(session_id)) + ".lock", timeout=1)

    def transaction_lock(self, session_id: str, *, timeout: float = 5) -> FileLock:
        """Serialize lifecycle transitions for one Codex session across hook processes."""
        return FileLock(str(self._path(session_id)) + ".txn.lock", timeout=timeout)

    def load(self, session_id: str) -> CodexSessionState | None:
        path = self._path(session_id)
        with self._lock(session_id):
            if not path.is_file():
                return None
            return CodexSessionState.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, state: CodexSessionState) -> None:
        path = self._path(state.session_id)
        with self._lock(state.session_id):
            temporary = path.with_suffix(".json.tmp")
            temporary.write_text(state.model_dump_json(indent=2) + "\n", encoding="utf-8")
            temporary.replace(path)

    def delete(self, session_id: str) -> None:
        path = self._path(session_id)
        with self._lock(session_id):
            path.unlink(missing_ok=True)


class WorkspaceTracker:
    # Lifecycle hooks have hard timeouts. A stalled Git probe must not consume
    # the whole hook budget and make the client appear frozen.
    GIT_PROBE_TIMEOUT_SECONDS = 2.0

    @staticmethod
    def _run(cwd: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        command = ["git", "-C", str(cwd), *args]
        try:
            return subprocess.run(
                command,
                text=True,
                capture_output=True,
                check=False,
                shell=False,
                timeout=WorkspaceTracker.GIT_PROBE_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return subprocess.CompletedProcess(
                command,
                returncode=124,
                stdout="",
                stderr=f"{type(exc).__name__}: git workspace probe unavailable",
            )

    @classmethod
    def _head(cls, cwd: Path) -> str | None:
        result = cls._run(cwd, ["rev-parse", "HEAD"])
        return result.stdout.strip() if result.returncode == 0 else None

    @classmethod
    def _dirty_paths(cls, cwd: Path) -> set[str]:
        # One status probe covers staged, unstaged, deleted, renamed/copied and
        # untracked paths. This replaces three sequential Git subprocesses in
        # every snapshot/finalization and keeps lifecycle locks short.
        result = cls._run(
            cwd,
            ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
        )
        if result.returncode != 0:
            return set()

        fields = result.stdout.split("\0")
        paths: set[str] = set()
        index = 0
        while index < len(fields):
            entry = fields[index]
            if not entry:
                index += 1
                continue
            if len(entry) < 4:
                index += 1
                continue

            status = entry[:2]
            path = entry[3:]
            if path:
                paths.add(path)

            # In porcelain v1 -z, rename/copy entries are followed by the
            # original path as a second NUL-delimited field.
            if "R" in status or "C" in status:
                index += 1
                if index < len(fields) and fields[index]:
                    paths.add(fields[index])
            index += 1
        return paths

    @staticmethod
    def _hash_path(cwd: Path, relative: str) -> str | None:
        path = (cwd / relative).resolve()
        try:
            path.relative_to(cwd.resolve())
        except ValueError:
            return None
        if not path.is_file():
            return None
        try:
            stat = path.stat()
            # Receipts only need change evidence. Avoid making lifecycle hooks hash
            # arbitrarily large generated artifacts synchronously.
            if stat.st_size > 8 * 1024 * 1024:
                return f"large:{stat.st_size}:{stat.st_mtime_ns}"
            digest = sha256()
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            return digest.hexdigest()
        except OSError:
            return None

    @classmethod
    def snapshot(cls, cwd: Path) -> WorkspaceSnapshot:
        cwd = Path(cwd).resolve()
        dirty = cls._dirty_paths(cwd)
        return WorkspaceSnapshot(
            cwd=str(cwd),
            head=cls._head(cwd),
            dirty_hashes={path: cls._hash_path(cwd, path) for path in sorted(dirty)},
        )

    @classmethod
    def changed_paths(cls, snapshot: WorkspaceSnapshot) -> list[str]:
        cwd = Path(snapshot.cwd)
        if not cwd.is_dir():
            return []
        current_dirty = cls._dirty_paths(cwd)
        changed: set[str] = set()

        for path in current_dirty | set(snapshot.dirty_hashes):
            before = snapshot.dirty_hashes.get(path, "__CLEAN__")
            after = cls._hash_path(cwd, path) if path in current_dirty else "__CLEAN__"
            if before != after:
                changed.add(path)

        current_head = cls._head(cwd)
        if snapshot.head and current_head and snapshot.head != current_head:
            result = cls._run(cwd, ["diff", "--name-only", "-z", f"{snapshot.head}..{current_head}"])
            if result.returncode == 0:
                changed.update(part for part in result.stdout.split("\0") if part)

        return sorted(changed)
