from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict
import yaml

from vaultin.errors import GovernanceBlocked


class AcceptanceStatus(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    PENDING = "PENDING"


class CriterionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    title: str
    status: AcceptanceStatus
    detail: str
    evidence: list[str] = []


class AcceptanceEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    source_spec: str
    criteria: dict[int, CriterionEvidence]

    @classmethod
    def load(cls, path: Path) -> "AcceptanceEvidence":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError("acceptance evidence must be a mapping")
        criteria_raw = raw.get("criteria", {})
        if not isinstance(criteria_raw, dict):
            raise ValueError("acceptance criteria must be a mapping")
        normalized: dict[int, dict] = {}
        for key, value in criteria_raw.items():
            criterion_id = int(key)
            if not isinstance(value, dict):
                raise ValueError(f"criterion {criterion_id} must be a mapping")
            normalized[criterion_id] = {"id": criterion_id, **value}
        evidence = cls.model_validate({**raw, "criteria": normalized})
        actual = set(evidence.criteria)
        if not actual:
            raise ValueError("acceptance evidence must contain at least one criterion")
        expected = set(range(1, max(actual) + 1))
        if actual != expected:
            raise ValueError(
                "acceptance evidence criteria must be contiguous from 1; "
                f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
            )
        return evidence

    def blocked(self) -> list[CriterionEvidence]:
        return [
            self.criteria[index]
            for index in sorted(self.criteria)
            if self.criteria[index].status is not AcceptanceStatus.PASS
        ]

    def machine_report(self) -> dict:
        blocked = self.blocked()
        return {
            "version": self.version,
            "source_spec": self.source_spec,
            "cutover_ready": not blocked,
            "criteria": {
                str(index): item.model_dump(mode="json")
                for index, item in sorted(self.criteria.items())
            },
            "blocked_criteria": [item.id for item in blocked],
        }


class AcceptanceGate:
    def __init__(self, evidence: AcceptanceEvidence) -> None:
        self.evidence = evidence

    def require_cutover_ready(self) -> None:
        blocked = self.evidence.blocked()
        if not blocked:
            return
        summary = "; ".join(
            f"{item.id}: {item.title} ({item.status.value})"
            for item in blocked
        )
        raise GovernanceBlocked(f"Vaultin cutover blocked by acceptance criteria: {summary}")
