from __future__ import annotations

from pathlib import Path
import re
import subprocess

from pydantic import BaseModel


class ProjectIdentity(BaseModel):
    slug: str
    repository: str | None = None
    local_path: str
    persistent: bool = True


class ProjectDiscovery:
    _SSH = re.compile(r"^(?:git@)?github\.com:(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$")
    _HTTPS = re.compile(r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$")
    _SSH_URL = re.compile(r"^ssh://git@github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$")

    @staticmethod
    def _slug(name: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
        if not normalized:
            raise ValueError("project slug is empty")
        return normalized

    @classmethod
    def normalize_remote(cls, remote: str) -> tuple[str, str] | None:
        remote = remote.strip()
        for pattern in (cls._SSH, cls._HTTPS, cls._SSH_URL):
            match = pattern.match(remote)
            if match:
                repo = match.group("repo")
                if repo.endswith(".git"):
                    repo = repo[:-4]
                return f"{match.group('owner')}/{repo}", cls._slug(repo)
        return None

    def detect(self, cwd: Path, *, persistent_signal: bool = False) -> ProjectIdentity | None:
        path = Path(cwd).resolve()
        try:
            result = subprocess.run(
                ["git", "-C", str(path), "remote", "get-url", "origin"],
                text=True,
                capture_output=True,
                check=False,
                shell=False,
                timeout=2,
            )
        except (OSError, subprocess.TimeoutExpired):
            result = None
        if result is not None and result.returncode == 0:
            parsed = self.normalize_remote(result.stdout)
            if parsed:
                repository, slug = parsed
                return ProjectIdentity(slug=slug, repository=repository, local_path=str(path), persistent=True)
        if persistent_signal:
            return ProjectIdentity(slug=self._slug(path.name), repository=None, local_path=str(path), persistent=True)
        return None
