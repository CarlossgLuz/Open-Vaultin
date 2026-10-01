from vaultin.index.search import SearchHit
from vaultin.knowledge.curator import CandidateKnowledge, KnowledgeCurator


curator = KnowledgeCurator()


def test_curator_updates_existing_matching_runbook() -> None:
    decision = curator.decide(
        candidate=CandidateKnowledge(kind="runbook", title="Pipeline timeout", scope="project"),
        hits=[SearchHit(path="vaults/projects/x/runbooks/pipeline-timeout.md", title="Pipeline timeout", score=9.1, scope="project", project="x")],
    )
    assert decision.action == "UPDATE"


def test_curator_ignores_ephemeral_execution_noise() -> None:
    decision = curator.decide(
        candidate=CandidateKnowledge(kind="observation", title="Temporary retry succeeded", durable=False),
        hits=[],
    )
    assert decision.action == "IGNORE"


def test_curator_creates_global_for_reusable_new_knowledge() -> None:
    decision = curator.decide(
        candidate=CandidateKnowledge(kind="pattern", title="Secure retry pattern", durable=True, reusable=True),
        hits=[],
    )
    assert decision.action == "CREATE"
    assert decision.destination == "global"
