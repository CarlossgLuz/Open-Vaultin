from pathlib import Path
import subprocess

import pytest

from vaultin.git.repo import GitRepo
from vaultin.models import ExecutionState
from vaultin.runtime.queue import SyncQueue
from vaultin.vaults.registry import ProjectVault
from vaultin.vaults.sync import ReplicaDivergence, VaultSync


class StaticRegistry:
    def __init__(self, project: ProjectVault) -> None:
        self.project = project

    def get(self, slug: str) -> ProjectVault | None:
        return self.project if slug == self.project.slug else None


class FakePush:
    def __init__(self) -> None:
        self.vaultin_push_count = 0
        self.replica_push_count = 0
        self.fail_replica_push_once = False

    def __call__(self, repo: GitRepo, repository_name: str) -> None:
        if repository_name == "acme/Vaultin":
            self.vaultin_push_count += 1
            return
        self.replica_push_count += 1
        if self.fail_replica_push_once:
            self.fail_replica_push_once = False
            raise RuntimeError("network down")


def _init_repo(path: Path) -> GitRepo:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Vaultin Test"], check=True)
    return GitRepo(path)


def _system(tmp_path: Path):
    vaultin_root = tmp_path / "Vaultin"
    vaultin_repo = _init_repo(vaultin_root)
    (vaultin_root / "vaults/projects/demo").mkdir(parents=True)
    (vaultin_root / "vaults/projects/demo/runbook.md").write_text("# Runbook\n", encoding="utf-8")
    (vaultin_root / "vaultin.yaml").write_text(
        "version: 1\n"
        "repository: acme/Vaultin\n"
        "project_vault_owner: acme\n"
        "project_vault_prefix: vault-\n"
        "fail_closed: true\n"
        "runtime_dir_name: .vaultin-runtime\n",
        encoding="utf-8",
    )
    vaultin_repo.commit(["."], "initial canonical")

    replica_root = tmp_path / "replicas/demo"
    _init_repo(replica_root)

    project = ProjectVault(
        slug="demo",
        source_repository="acme/demo",
        canonical_path=vaultin_root / "vaults/projects/demo",
        replica_repository="acme/vault-demo",
    )
    queue = SyncQueue(tmp_path / "runtime/sync-queue.jsonl")
    push = FakePush()
    sync = VaultSync(
        root=vaultin_root,
        registry=StaticRegistry(project),
        queue=queue,
        replica_root=tmp_path / "replicas",
        push=push,
    )
    return sync, vaultin_root, replica_root, push


def test_projection_copies_only_project_vault_content(tmp_path: Path) -> None:
    sync, vaultin_root, replica_root, _ = _system(tmp_path)
    result = sync.project("demo", execution_id="exec_1")

    assert (replica_root / "runbook.md").read_text(encoding="utf-8") == "# Runbook\n"
    assert not (replica_root / "vaultin.yaml").exists()
    assert (replica_root / ".vaultin-replica.json").is_file()
    assert result.vaultin_sha
    assert result.replica_sha
    assert result.state == ExecutionState.COMPLETED


def test_replica_divergence_never_overwrites_canonical(tmp_path: Path) -> None:
    sync, vaultin_root, replica_root, _ = _system(tmp_path)
    canonical = vaultin_root / "vaults/projects/demo/runbook.md"
    sync.project("demo", execution_id="exec_1")

    (replica_root / "runbook.md").write_text("external edit\n", encoding="utf-8")
    GitRepo(replica_root).commit(["runbook.md"], "external")

    with pytest.raises(ReplicaDivergence):
        sync.project("demo", execution_id="exec_2")

    assert canonical.read_text(encoding="utf-8") == "# Runbook\n"


def test_failed_replica_push_enters_partial_sync_and_retries_once(tmp_path: Path) -> None:
    sync, _, _, push = _system(tmp_path)
    push.fail_replica_push_once = True
    first = sync.project("demo", execution_id="exec_3")
    assert first.state == ExecutionState.PARTIAL_SYNC

    second = sync.reconcile_pending()
    assert second[0].state == ExecutionState.COMPLETED
    assert push.replica_push_count == 2
    assert push.vaultin_push_count == 1


def test_existing_unmanaged_replica_is_never_overwritten_on_first_sync(tmp_path: Path) -> None:
    sync, vaultin_root, replica_root, _ = _system(tmp_path)
    unmanaged = replica_root / "important.txt"
    unmanaged.write_text("do not overwrite\n", encoding="utf-8")
    GitRepo(replica_root).commit(["important.txt"], "existing unmanaged content")

    with pytest.raises(ReplicaDivergence, match="unmanaged"):
        sync.project("demo", execution_id="exec_unmanaged")

    assert unmanaged.read_text(encoding="utf-8") == "do not overwrite\n"
    assert (vaultin_root / "vaults/projects/demo/runbook.md").is_file()
