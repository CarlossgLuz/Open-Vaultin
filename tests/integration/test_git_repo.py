from pathlib import Path
import subprocess

from vaultin.git.repo import GitCommandError, GitRepo


def _init(path: Path) -> GitRepo:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Vaultin Test"], check=True)
    return GitRepo(path)


def test_commit_returns_current_sha_and_is_idempotent_when_clean(tmp_path: Path) -> None:
    repo = _init(tmp_path / "repo")
    (repo.path / "a.txt").write_text("one\n", encoding="utf-8")
    first = repo.commit(["a.txt"], "add a")
    second = repo.commit(["a.txt"], "no-op")
    assert first == second == repo.current_sha()


def test_git_commands_do_not_use_shell(tmp_path: Path) -> None:
    repo = _init(tmp_path / "repo")
    hostile = repo.path / "file;echo-pwned.txt"
    hostile.write_text("safe\n", encoding="utf-8")
    sha = repo.commit([hostile.name], "safe path")
    assert sha == repo.current_sha()
    assert not (repo.path / "pwned.txt").exists()


def test_force_commit_can_publish_explicitly_ignored_receipt(tmp_path: Path) -> None:
    import pytest

    repo = _init(tmp_path / "repo")
    (repo.path / ".gitignore").write_text(
        "memory/execution-receipts/\n",
        encoding="utf-8",
    )
    repo.commit([".gitignore"], "ignore receipts")

    receipt = repo.path / "memory/execution-receipts/2026/10/exec.md"
    receipt.parent.mkdir(parents=True)
    receipt.write_text("# Receipt\n", encoding="utf-8")

    with pytest.raises(GitCommandError):
        repo.commit(["memory/execution-receipts/2026/10/exec.md"], "normal add")

    sha = repo.commit(
        ["memory/execution-receipts/2026/10/exec.md"],
        "explicit receipt publication",
        force=True,
    )
    assert sha == repo.current_sha()
