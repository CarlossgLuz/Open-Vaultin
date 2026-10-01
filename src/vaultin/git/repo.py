from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Sequence


class GitCommandError(RuntimeError):
    pass


class GitRepo:
    def __init__(self, path: Path) -> None:
        self.path = Path(path).resolve()

    def _run(self, args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        command = ["git", "-C", str(self.path), *args]
        try:
            result = subprocess.run(
                command,
                text=True,
                capture_output=True,
                shell=False,
                check=False,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GitCommandError(
                f"git {' '.join(args)} failed: {type(exc).__name__}"
            ) from exc
        if check and result.returncode != 0:
            message = (result.stderr or result.stdout).strip()
            raise GitCommandError(f"git {' '.join(args)} failed: {message}")
        return result

    def has_commits(self) -> bool:
        result = self._run(["rev-parse", "--verify", "HEAD"], check=False)
        return result.returncode == 0

    def current_sha(self) -> str:
        return self._run(["rev-parse", "HEAD"]).stdout.strip()

    def current_branch(self) -> str:
        branch = self._run(["branch", "--show-current"]).stdout.strip()
        if not branch:
            raise GitCommandError("detached HEAD is not supported for this operation")
        return branch

    def commit(self, paths: list[str], message: str, *, force: bool = False) -> str:
        if not paths:
            raise ValueError("commit paths must not be empty")
        add_args = ["add"]
        if force:
            add_args.append("--force")
        add_args.extend(["--", *paths])
        self._run(add_args)
        diff = self._run(["diff", "--cached", "--quiet"], check=False)
        if diff.returncode == 0:
            return self.current_sha()
        if diff.returncode != 1:
            raise GitCommandError(f"git diff --cached --quiet failed: {diff.stderr.strip()}")
        self._run(["commit", "-m", message])
        return self.current_sha()

    def has_remote(self, name: str = "origin") -> bool:
        result = self._run(["remote", "get-url", name], check=False)
        return result.returncode == 0

    def fetch(self, remote: str = "origin") -> None:
        self._run(["fetch", remote])

    def remote_head(self, remote: str = "origin") -> str | None:
        if not self.has_remote(remote):
            return None
        branch = self.current_branch()
        result = self._run(["ls-remote", remote, f"refs/heads/{branch}"], check=False)
        if result.returncode != 0:
            raise GitCommandError(f"git ls-remote failed: {(result.stderr or result.stdout).strip()}")
        line = result.stdout.strip()
        if not line:
            return None
        return line.split()[0]

    def push(self, remote: str = "origin") -> None:
        self._run(["push", "-u", remote, "HEAD"])
        remote_sha = self.remote_head(remote)
        if remote_sha is not None and remote_sha != self.current_sha():
            raise GitCommandError(
                f"remote verification mismatch: local={self.current_sha()} remote={remote_sha}"
            )

    @classmethod
    def clone(cls, remote_url: str, destination: Path) -> "GitRepo":
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                ["git", "clone", remote_url, str(destination)],
                text=True,
                capture_output=True,
                shell=False,
                check=False,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GitCommandError(f"git clone failed: {type(exc).__name__}") from exc
        if result.returncode != 0:
            raise GitCommandError(f"git clone failed: {(result.stderr or result.stdout).strip()}")
        return cls(destination)
