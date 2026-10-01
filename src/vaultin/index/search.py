from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
import sqlite3
from typing import Any

import yaml


@dataclass(frozen=True)
class SearchHit:
    path: str
    title: str
    score: float
    scope: str
    project: str | None = None


class SearchIndex:
    SEARCH_ROOTS = ("knowledge", "memory", "vaults/projects")

    def __init__(self, root: Path, database_path: Path) -> None:
        self.root = Path(root)
        self.database_path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _parse_markdown(path: Path, relative: Path) -> tuple[str, str, list[str], str, str | None]:
        text = path.read_text(encoding="utf-8", errors="replace")
        metadata: dict[str, Any] = {}
        body = text
        if text.startswith("---\n"):
            end = text.find("\n---\n", 4)
            if end != -1:
                raw = text[4:end]
                loaded = yaml.safe_load(raw) or {}
                if isinstance(loaded, dict):
                    metadata = loaded
                body = text[end + 5 :]
        title = str(metadata.get("title") or "")
        if not title:
            for line in body.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        if not title:
            title = path.stem.replace("-", " ").title()
        tags_raw = metadata.get("tags", [])
        if isinstance(tags_raw, str):
            tags = [tags_raw]
        elif isinstance(tags_raw, list):
            tags = [str(item) for item in tags_raw]
        else:
            tags = []
        parts = relative.parts
        project: str | None = None
        scope = "global"
        if len(parts) >= 3 and parts[0] == "vaults" and parts[1] == "projects":
            project = parts[2]
            scope = "project"
        return title, body, tags, scope, project

    def _markdown_files(self) -> list[Path]:
        result: set[Path] = set()
        for rel_root in self.SEARCH_ROOTS:
            base = self.root / rel_root
            if base.is_dir():
                result.update(path for path in base.rglob("*.md") if path.is_file())
        return sorted(result)

    def rebuild(self) -> int:
        with closing(self._connect()) as connection:
            connection.execute("DROP TABLE IF EXISTS documents")
            connection.execute(
                """
                CREATE VIRTUAL TABLE documents USING fts5(
                    path UNINDEXED,
                    title,
                    body,
                    tags,
                    scope UNINDEXED,
                    project UNINDEXED,
                    updated_at UNINDEXED
                )
                """
            )
            count = 0
            for path in self._markdown_files():
                relative = path.relative_to(self.root)
                title, body, tags, scope, project = self._parse_markdown(path, relative)
                connection.execute(
                    "INSERT INTO documents(path, title, body, tags, scope, project, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        relative.as_posix(),
                        title,
                        body,
                        " ".join(tags),
                        scope,
                        project,
                        datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat(),
                    ),
                )
                count += 1
            connection.commit()
        return count

    @staticmethod
    def _fts_query(query: str) -> str:
        tokens = re.findall(r"[\w-]+", query, flags=re.UNICODE)
        if not tokens:
            return '""'
        escaped = [token.replace('"', '""') for token in tokens]
        return " AND ".join(f'"{token}"' for token in escaped)

    def search(self, query: str, *, current_project: str | None = None, limit: int = 20) -> list[SearchHit]:
        if not self.database_path.exists():
            self.rebuild()
        fts_query = self._fts_query(query)
        if fts_query == '""':
            return []
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT path, title, scope, project, bm25(documents, 0.0, 4.0, 1.0, 2.0) AS rank
                FROM documents
                WHERE documents MATCH ?
                ORDER BY rank ASC
                LIMIT ?
                """,
                (fts_query, max(limit * 4, limit)),
            ).fetchall()
        hits = []
        for row in rows:
            base_score = -float(row["rank"])
            boost = 5.0 if current_project and row["project"] == current_project else 0.0
            hits.append(
                SearchHit(
                    path=row["path"],
                    title=row["title"],
                    score=base_score + boost,
                    scope=row["scope"],
                    project=row["project"],
                )
            )
        hits.sort(key=lambda item: (-item.score, item.path))
        return hits[:limit]
