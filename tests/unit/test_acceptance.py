from pathlib import Path

import pytest

from vaultin.acceptance import AcceptanceEvidence


def _write(path: Path, criteria: str) -> Path:
    path.write_text(
        "version: 1\n"
        "source_spec: docs/architecture.md\n"
        "criteria:\n"
        + criteria,
        encoding="utf-8",
    )
    return path


def test_acceptance_allows_contiguous_project_specific_criteria(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "evidence.yaml",
        "  1:\n"
        "    title: First\n"
        "    status: PASS\n"
        "    detail: ok\n"
        "    evidence: []\n"
        "  2:\n"
        "    title: Second\n"
        "    status: BLOCKED\n"
        "    detail: pending\n"
        "    evidence: []\n",
    )
    evidence = AcceptanceEvidence.load(path)
    assert set(evidence.criteria) == {1, 2}


def test_acceptance_rejects_gaps(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "evidence.yaml",
        "  1:\n"
        "    title: First\n"
        "    status: PASS\n"
        "    detail: ok\n"
        "    evidence: []\n"
        "  3:\n"
        "    title: Third\n"
        "    status: PASS\n"
        "    detail: ok\n"
        "    evidence: []\n",
    )
    with pytest.raises(ValueError, match="contiguous"):
        AcceptanceEvidence.load(path)
