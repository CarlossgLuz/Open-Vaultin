from pathlib import Path

from vaultin.projects.discovery import ProjectIdentity
from vaultin.vaults.registry import RemoteRepository, VaultRegistry


class FakeGitHub:
    def __init__(self, owner: str = "acme") -> None:
        self.owner = owner
        self.created = []

    def create_private_repository(self, name: str) -> RemoteRepository:
        self.created.append({"owner": self.owner, "name": name, "private": True})
        return RemoteRepository(full_name=f"{self.owner}/{name}", private=True)


def _write_config(
    root: Path,
    *,
    repository: str = "acme/Vaultin",
    owner: str = "acme",
    prefix: str = "vault-",
) -> None:
    (root / "vaultin.yaml").write_text(
        "\n".join([
            "version: 1",
            f"repository: {repository}",
            f"project_vault_owner: {owner}",
            f"project_vault_prefix: {prefix}",
            "fail_closed: true",
            "runtime_dir_name: .vaultin-runtime",
            "",
        ]),
        encoding="utf-8",
    )


def test_new_real_project_creates_private_personal_vault(tmp_path: Path) -> None:
    _write_config(tmp_path)
    fake_github = FakeGitHub()
    registry = VaultRegistry(tmp_path, github=fake_github)
    identity = ProjectIdentity(
        slug="demo-app",
        repository="acme/demo-app",
        local_path=str(tmp_path / "demo-app"),
        persistent=True,
    )
    project = registry.ensure_project(identity)
    assert fake_github.created == [{
        "owner": "acme",
        "name": "vault-demo-app",
        "private": True,
    }]
    assert project.canonical_path.as_posix().endswith("vaults/projects/demo-app")
    assert project.replica_repository == "acme/vault-demo-app"


def test_existing_project_is_idempotent(tmp_path: Path) -> None:
    _write_config(tmp_path)
    fake_github = FakeGitHub()
    registry = VaultRegistry(tmp_path, github=fake_github)
    identity = ProjectIdentity(slug="demo", repository="acme/demo", local_path="/tmp/demo", persistent=True)
    first = registry.ensure_project(identity)
    second = registry.ensure_project(identity)
    assert first == second
    assert len(fake_github.created) == 1


def test_project_vault_owner_and_prefix_come_from_config(tmp_path: Path) -> None:
    _write_config(
        tmp_path,
        repository="acme/vaultin",
        owner="acme",
        prefix="knowledge-",
    )
    fake_github = FakeGitHub(owner="acme")
    registry = VaultRegistry(tmp_path, github=fake_github)

    project = registry.ensure_project(
        ProjectIdentity(
            slug="demo",
            repository="acme/demo",
            local_path=str(tmp_path / "demo"),
            persistent=True,
        )
    )

    assert fake_github.created == [
        {"owner": "acme", "name": "knowledge-demo", "private": True}
    ]
    assert project.replica_repository == "acme/knowledge-demo"
