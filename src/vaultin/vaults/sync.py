from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Callable, Protocol

from filelock import FileLock
from pydantic import BaseModel, Field

from vaultin.config import load_settings
from vaultin.git.repo import GitRepo
from vaultin.models import ExecutionState
from vaultin.runtime.queue import SyncQueue, SyncQueueItem
from vaultin.vaults.registry import ProjectVault


class ReplicaDivergence(RuntimeError):
    pass


class ProjectRegistry(Protocol):
    def get(self, slug: str) -> ProjectVault | None: ...


class SyncResult(BaseModel):
    project: str
    execution_id: str
    state: ExecutionState
    vaultin_sha: str | None = None
    replica_sha: str | None = None
    pending_repositories: list[str] = Field(default_factory=list)


PushCallable = Callable[[GitRepo, str], None]


class VaultSync:
    def __init__(
        self,
        *,
        root: Path,
        registry: ProjectRegistry,
        queue: SyncQueue,
        replica_root: Path,
        push: PushCallable | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.settings = load_settings(self.root)
        self.canonical_repository = self.settings.repository
        self.replica_repository_prefix = (
            f"{self.settings.project_vault_owner}/"
            f"{self.settings.project_vault_prefix}"
        )
        self.registry = registry
        self.queue = queue
        self.replica_root = Path(replica_root).resolve()
        self._push = push or self._default_push
        self._state_path = self.root / ".vaultin-runtime" / "replica-state.json"
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_lock = FileLock(str(self._state_path) + ".lock")

    @staticmethod
    def _default_push(repo: GitRepo, repository_name: str) -> None:
        repo.push()

    def _load_state(self) -> dict[str, dict[str, str]]:
        if not self._state_path.is_file():
            return {}
        raw = json.loads(self._state_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise RuntimeError("invalid replica sync state")
        return raw

    def _save_replica_state(self, slug: str, sha: str) -> None:
        with self._state_lock:
            state = self._load_state()
            state[slug] = {"replica_sha": sha}
            temporary = self._state_path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            temporary.replace(self._state_path)

    def _expected_replica_sha(self, slug: str) -> str | None:
        with self._state_lock:
            return self._load_state().get(slug, {}).get("replica_sha")

    def _replica_repo(self, project: ProjectVault) -> GitRepo:
        path = self.replica_root / project.slug
        if not (path / ".git").is_dir():
            remote_url = f"https://github.com/{project.replica_repository}.git"
            return GitRepo.clone(remote_url, path)
        return GitRepo(path)

    def _assert_no_divergence(self, project: ProjectVault, repo: GitRepo) -> None:
        expected = self._expected_replica_sha(project.slug)
        if expected is None:
            if repo.has_commits():
                raise ReplicaDivergence(
                    f"unmanaged existing replica for {project.slug}: "
                    "Vaultin has no trusted replica state for this repository"
                )
            return
        local = repo.current_sha()
        if local != expected:
            raise ReplicaDivergence(
                f"replica divergence for {project.slug}: expected {expected}, local {local}"
            )
        remote = repo.remote_head() if repo.has_remote() else None
        if remote is not None and remote != expected:
            raise ReplicaDivergence(
                f"replica divergence for {project.slug}: expected {expected}, remote {remote}"
            )

    @staticmethod
    def _clear_replica_worktree(replica_path: Path) -> None:
        for child in replica_path.iterdir():
            if child.name == ".git":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    @staticmethod
    def _copy_canonical(source: Path, destination: Path) -> None:
        for child in source.iterdir():
            target = destination / child.name
            if child.is_dir():
                shutil.copytree(child, target)
            else:
                shutil.copy2(child, target)

    def project(self, slug: str, *, execution_id: str) -> SyncResult:
        project = self.registry.get(slug)
        if project is None:
            raise KeyError(f"unknown project vault: {slug}")
        if not project.canonical_path.is_dir():
            raise FileNotFoundError(f"canonical project vault not found: {project.canonical_path}")

        vaultin_repo = GitRepo(self.root)
        replica_repo = self._replica_repo(project)
        self._assert_no_divergence(project, replica_repo)

        canonical_rel = project.canonical_path.relative_to(self.root).as_posix()
        vaultin_sha = vaultin_repo.commit(
            [canonical_rel],
            f"vault({slug}): sync {execution_id}",
        )

        self._clear_replica_worktree(replica_repo.path)
        self._copy_canonical(project.canonical_path, replica_repo.path)
        manifest = {
            "project": slug,
            "canonical_repository": self.canonical_repository,
            "canonical_path": canonical_rel,
            "source_execution_id": execution_id,
            "canonical_sha": vaultin_sha,
        }
        (replica_repo.path / ".vaultin-replica.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        replica_sha = replica_repo.commit(["."], f"vault({slug}): mirror {execution_id}")
        self._save_replica_state(slug, replica_sha)

        failures: list[tuple[str, GitRepo, str]] = []
        for repository_name, repo, sha in (
            (self.canonical_repository, vaultin_repo, vaultin_sha),
            (project.replica_repository, replica_repo, replica_sha),
        ):
            try:
                self._push(repo, repository_name)
            except Exception:
                failures.append((repository_name, repo, sha))

        if not failures:
            return SyncResult(
                project=slug,
                execution_id=execution_id,
                state=ExecutionState.COMPLETED,
                vaultin_sha=vaultin_sha,
                replica_sha=replica_sha,
            )

        state = ExecutionState.PENDING_SYNC if len(failures) == 2 else ExecutionState.PARTIAL_SYNC
        for repository_name, _, sha in failures:
            self.queue.enqueue(
                SyncQueueItem(
                    execution_id=execution_id,
                    repository=repository_name,
                    local_sha=sha,
                    state=state.value,
                )
            )
        return SyncResult(
            project=slug,
            execution_id=execution_id,
            state=state,
            vaultin_sha=vaultin_sha,
            replica_sha=replica_sha,
            pending_repositories=[name for name, _, _ in failures],
        )

    def _repo_for_queue_item(self, item: SyncQueueItem) -> tuple[GitRepo, str]:
        if item.repository == self.canonical_repository:
            return GitRepo(self.root), "global"
        prefix = self.replica_repository_prefix
        if not item.repository.startswith(prefix):
            raise RuntimeError(f"unsupported queued repository: {item.repository}")
        slug = item.repository[len(prefix):]
        return GitRepo(self.replica_root / slug), slug

    def reconcile_pending(self) -> list[SyncResult]:
        results: list[SyncResult] = []
        for item in list(self.queue.pending()):
            retrying = self.queue.replace_state(item, ExecutionState.RETRYING_SYNC.value)
            repo, slug = self._repo_for_queue_item(retrying)
            if repo.current_sha() != retrying.local_sha:
                self.queue.replace_state(retrying, ExecutionState.PARTIAL_SYNC.value)
                results.append(
                    SyncResult(
                        project=slug,
                        execution_id=retrying.execution_id,
                        state=ExecutionState.PARTIAL_SYNC,
                        pending_repositories=[retrying.repository],
                    )
                )
                continue
            try:
                self._push(repo, retrying.repository)
            except Exception:
                self.queue.replace_state(retrying, ExecutionState.PARTIAL_SYNC.value)
                results.append(
                    SyncResult(
                        project=slug,
                        execution_id=retrying.execution_id,
                        state=ExecutionState.PARTIAL_SYNC,
                        pending_repositories=[retrying.repository],
                    )
                )
                continue
            self.queue.remove(retrying)
            results.append(
                SyncResult(
                    project=slug,
                    execution_id=retrying.execution_id,
                    state=ExecutionState.COMPLETED,
                    vaultin_sha=retrying.local_sha if retrying.repository == self.canonical_repository else None,
                    replica_sha=retrying.local_sha if retrying.repository != self.canonical_repository else None,
                )
            )
        return results
