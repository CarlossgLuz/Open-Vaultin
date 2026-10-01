from __future__ import annotations

from pathlib import Path
from typing import Protocol

from filelock import FileLock
from pydantic import BaseModel
import yaml

from vaultin.config import load_settings
from vaultin.projects.discovery import ProjectIdentity


class RemoteRepository(BaseModel):
    full_name: str
    private: bool


class GitHubRepositoryCreator(Protocol):
    def create_private_repository(self, name: str) -> RemoteRepository: ...


class ProjectVault(BaseModel):
    slug: str
    source_repository: str | None = None
    canonical_path: Path
    replica_repository: str


class VaultRegistry:
    def __init__(self, root: Path, *, github: GitHubRepositoryCreator) -> None:
        self.root = Path(root)
        self.github = github
        self.settings = load_settings(self.root)
        self.registry_path = self.root / "vaults" / "registry.yaml"
        self._lock = FileLock(str(self.registry_path) + ".lock")

    def _read(self) -> dict:
        if not self.registry_path.is_file():
            return {"version": 1, "projects": {}}
        raw = yaml.safe_load(self.registry_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError("vaults/registry.yaml must be a mapping")
        raw.setdefault("version", 1)
        raw.setdefault("projects", {})
        if not isinstance(raw["projects"], dict):
            raise ValueError("vaults registry projects must be a mapping")
        return raw

    def _project_from_entry(self, slug: str, entry: dict) -> ProjectVault:
        canonical = self.root / entry["canonical_path"]
        return ProjectVault(
            slug=slug,
            source_repository=entry.get("source_repository"),
            canonical_path=canonical,
            replica_repository=entry["replica_repository"],
        )

    def ensure_project(self, identity: ProjectIdentity) -> ProjectVault:
        if not identity.persistent:
            raise ValueError("cannot create a vault for a non-persistent project")
        with self._lock:
            data = self._read()
            existing = data["projects"].get(identity.slug)
            if existing:
                return self._project_from_entry(identity.slug, existing)

            canonical_rel = Path("vaults") / "projects" / identity.slug
            canonical = self.root / canonical_rel
            canonical.mkdir(parents=True, exist_ok=True)

            replica_name = f"{self.settings.project_vault_prefix}{identity.slug}"
            remote = self.github.create_private_repository(replica_name)
            if not remote.private:
                raise RuntimeError(f"replica repository must be private: {remote.full_name}")
            expected = f"{self.settings.project_vault_owner}/{replica_name}"
            if remote.full_name != expected:
                raise RuntimeError(f"replica repository owner mismatch: expected {expected}, got {remote.full_name}")

            entry = {
                "source_repository": identity.repository,
                "canonical_path": canonical_rel.as_posix(),
                "replica_repository": remote.full_name,
                "sync": "automatic",
            }
            data["projects"][identity.slug] = entry
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.registry_path.with_suffix(".yaml.tmp")
            temporary.write_text(yaml.safe_dump(data, sort_keys=True), encoding="utf-8")
            temporary.replace(self.registry_path)
            return self._project_from_entry(identity.slug, entry)

    def get(self, slug: str) -> ProjectVault | None:
        with self._lock:
            data = self._read()
            entry = data["projects"].get(slug)
            return self._project_from_entry(slug, entry) if entry else None

    def all(self) -> list[ProjectVault]:
        with self._lock:
            data = self._read()
            return [self._project_from_entry(slug, entry) for slug, entry in sorted(data["projects"].items())]
