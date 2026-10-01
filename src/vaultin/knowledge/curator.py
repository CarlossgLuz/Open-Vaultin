from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from vaultin.index.search import SearchHit


CuratorAction = Literal["UPDATE", "APPEND", "SUPERSEDE", "CREATE", "IGNORE"]


class CandidateKnowledge(BaseModel):
    kind: str
    title: str
    scope: Literal["project", "global", "mixed"] = "project"
    durable: bool = True
    reusable: bool = False


class CuratorDecision(BaseModel):
    action: CuratorAction
    destination: Literal["project", "global", "mixed", "none"]
    target_path: str | None = None
    reason: str


class KnowledgeCurator:
    def decide(self, candidate: CandidateKnowledge, hits: list[SearchHit]) -> CuratorDecision:
        if not candidate.durable:
            return CuratorDecision(
                action="IGNORE",
                destination="none",
                reason="candidate is not durable knowledge",
            )

        normalized_title = candidate.title.casefold().strip()
        for hit in hits:
            if hit.title.casefold().strip() == normalized_title or hit.score >= 5.0:
                return CuratorDecision(
                    action="UPDATE",
                    destination="project" if hit.scope == "project" else "global",
                    target_path=hit.path,
                    reason="relevant canonical knowledge already exists",
                )

        destination: Literal["project", "global", "mixed"]
        if candidate.reusable or candidate.scope == "global":
            destination = "global"
        elif candidate.scope == "mixed":
            destination = "mixed"
        else:
            destination = "project"
        return CuratorDecision(
            action="CREATE",
            destination=destination,
            reason="no sufficiently relevant canonical knowledge exists",
        )
