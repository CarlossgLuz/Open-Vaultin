from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field


class ReceiptData(BaseModel):
    execution_id: str
    project: str | None = None
    objective: str
    agents: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    files_changed: list[str] = Field(default_factory=list)
    validations: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    git: dict[str, str] = Field(default_factory=dict)
    vaults_updated: list[str] = Field(default_factory=list)
    status: str
    pending: list[str] = Field(default_factory=list)


class ReceiptWriter:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def write(self, data: ReceiptData, *, now: datetime | None = None) -> Path:
        stamp = now or datetime.now(UTC)
        target = self.root / "memory" / "execution-receipts" / f"{stamp:%Y}" / f"{stamp:%m}" / f"{data.execution_id}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        files = data.files_changed or ["nenhum arquivo alterado"]
        validations = data.validations or ["nenhuma validação registrada"]
        git_lines = [f"- {key}: {value}" for key, value in sorted(data.git.items())] or ["- n/a"]
        pending = data.pending or ["nenhuma"]
        body = "\n".join(
            [
                "---",
                f"execution_id: {data.execution_id}",
                f"project: {data.project or 'global'}",
                f"status: {data.status}",
                f"created_at: {stamp.isoformat()}",
                "---",
                "",
                f"# Execution Receipt — {data.execution_id}",
                "",
                "## Objetivo",
                data.objective,
                "",
                "## Alterações",
                *[f"- {item}" for item in files],
                "",
                "## Validações",
                *[f"- {item}" for item in validations],
                "",
                "## Git",
                *git_lines,
                "",
                "## Pendências",
                *[f"- {item}" for item in pending],
                "",
            ]
        )
        target.write_text(body, encoding="utf-8")
        return target
