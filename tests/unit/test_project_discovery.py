from pathlib import Path
import subprocess

from vaultin.projects.discovery import ProjectDiscovery


def _git(tmp_path: Path, remote: str | None = None) -> Path:
    repo = tmp_path / "demo-app"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    if remote:
        subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", remote], check=True)
    return repo


def test_git_remote_is_primary_project_identity(tmp_path: Path) -> None:
    repo = _git(tmp_path, "git@github.com:acme/demo-app.git")
    identity = ProjectDiscovery().detect(repo)
    assert identity is not None
    assert identity.slug == "demo-app"
    assert identity.repository == "acme/demo-app"


def test_https_git_remote_is_normalized(tmp_path: Path) -> None:
    repo = _git(tmp_path, "https://github.com/acme/sample-app.git")
    identity = ProjectDiscovery().detect(repo)
    assert identity is not None
    assert identity.slug == "sample-app"
    assert identity.repository == "acme/sample-app"


def test_scratch_directory_does_not_create_project(tmp_path: Path) -> None:
    assert ProjectDiscovery().detect(tmp_path) is None


def test_project_discovery_uses_bounded_git_timeout(tmp_path: Path, monkeypatch) -> None:
    observed = {}

    def fake_run(*args, **kwargs):
        observed["timeout"] = kwargs.get("timeout")
        return subprocess.CompletedProcess(args[0], returncode=1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    ProjectDiscovery().detect(tmp_path)

    assert observed["timeout"] == 2
