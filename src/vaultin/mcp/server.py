from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Protocol

import yaml

from vaultin.git.repo import GitRepo
from vaultin.index.search import SearchIndex
from vaultin.ledger.receipt import ReceiptData, ReceiptWriter


class CanonicalPublisher(Protocol):
    def publish(self, paths: list[str], message: str) -> dict[str, str]: ...


class GitCanonicalPublisher:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()

    def publish(self, paths: list[str], message: str) -> dict[str, str]:
        repo = GitRepo(self.root)
        sha = repo.commit(paths, message)
        repo.push()
        return {"vaultin": sha}


class VaultinMCPService:
    """Narrow canonical Vaultin operations exposed to MCP hosts."""

    def __init__(
        self,
        root: Path,
        *,
        sync_callback: Callable[[str], dict] | None = None,
        publisher: CanonicalPublisher | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.runtime = self.root / ".vaultin-runtime"
        self.index = SearchIndex(self.root, self.runtime / "search.db")
        self.sync_callback = sync_callback
        self.publisher = publisher

    @staticmethod
    def _safe_relative(relative_path: str) -> Path:
        rel = Path(relative_path)
        if rel.is_absolute() or ".." in rel.parts or not rel.parts:
            raise ValueError("invalid relative path")
        return rel

    def rebuild_index(self) -> dict:
        return {"documents": self.index.rebuild()}

    def search_knowledge(self, query: str, current_project: str | None = None, limit: int = 20) -> list[dict]:
        return [
            {
                "path": hit.path,
                "title": hit.title,
                "score": hit.score,
                "scope": hit.scope,
                "project": hit.project,
            }
            for hit in self.index.search(query, current_project=current_project, limit=limit)
        ]

    def read_canonical(self, relative_path: str) -> dict:
        rel = self._safe_relative(relative_path)
        allowed = rel.parts[0] in {"knowledge", "memory", "vaults", "agents", ".agents", "policies", "workflows"}
        if not allowed:
            raise ValueError("path is outside the canonical Vaultin surface")
        target = (self.root / rel).resolve()
        if self.root not in target.parents and target != self.root:
            raise ValueError("invalid relative path")
        if not target.is_file():
            raise FileNotFoundError(relative_path)
        return {"path": rel.as_posix(), "content": target.read_text(encoding="utf-8")}

    def write_project_note(
        self,
        project: str,
        relative_path: str,
        content: str,
        *,
        publish: bool = False,
    ) -> dict:
        if not project or "/" in project or "\\" in project or project in {".", ".."}:
            raise ValueError("invalid project slug")
        rel = self._safe_relative(relative_path)
        if rel.suffix.lower() != ".md":
            raise ValueError("project vault writes must target Markdown files")
        base = (self.root / "vaults" / "projects" / project).resolve()
        if not base.is_dir():
            raise FileNotFoundError(f"canonical project vault not found: {project}")
        target = (base / rel).resolve()
        if base not in target.parents:
            raise ValueError("invalid relative path")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        canonical_path = target.relative_to(self.root).as_posix()
        result: dict = {
            "path": canonical_path,
            "bytes": len(content.encode("utf-8")),
        }
        if publish:
            if self.publisher is None:
                raise RuntimeError("canonical Git publication is not configured")
            result["git"] = self.publisher.publish(
                [canonical_path],
                f"vault({project}): update {rel.as_posix()}",
            )
        return result

    def inspect_registry(self) -> dict:
        path = self.root / "vaults" / "registry.yaml"
        if not path.is_file():
            return {"version": 1, "projects": {}}
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError("invalid vault registry")
        return raw

    def write_receipt(self, data: dict) -> dict:
        receipt = ReceiptData.model_validate(data)
        path = ReceiptWriter(self.root).write(receipt)
        return {"path": path.relative_to(self.root).as_posix()}

    def request_sync(self, project: str) -> dict:
        if self.sync_callback is None:
            return {"project": project, "status": "not-configured"}
        return self.sync_callback(project)


def build_mcp_server(root: Path, *, allow_publish: bool = False):
    from mcp.server import MCPServer

    publisher = GitCanonicalPublisher(root) if allow_publish else None
    service = VaultinMCPService(root, publisher=publisher)
    server = MCPServer("Vaultin")

    @server.tool()
    def search_knowledge(query: str, current_project: str | None = None, limit: int = 20) -> list[dict]:
        """Search canonical Vaultin knowledge using the local FTS index."""
        return service.search_knowledge(query, current_project, limit)

    @server.tool()
    def read_canonical(relative_path: str) -> dict:
        """Read an allowed canonical Vaultin artifact."""
        return service.read_canonical(relative_path)

    @server.tool()
    def write_project_note(
        project: str,
        relative_path: str,
        content: str,
        publish: bool = False,
    ) -> dict:
        """Write Markdown to the canonical project vault; optionally commit/push when enabled."""
        return service.write_project_note(project, relative_path, content, publish=publish)

    @server.tool()
    def inspect_registry() -> dict:
        """Read the canonical project vault registry."""
        return service.inspect_registry()

    return server


def main() -> None:
    root_marker = Path.home() / ".vaultin" / "root"
    root_value = os.environ.get(
        "VAULTIN_ROOT",
        root_marker.read_text(encoding="utf-8").strip() if root_marker.is_file() else "",
    )
    if not root_value:
        raise RuntimeError("Vaultin root is not configured")
    allow_publish = os.environ.get("VAULTIN_MCP_ALLOW_PUBLISH", "").casefold() in {"1", "true", "yes"}
    build_mcp_server(Path(root_value), allow_publish=allow_publish).run()
