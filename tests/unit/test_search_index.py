from pathlib import Path

from vaultin.index.search import SearchIndex


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_current_project_is_boosted_but_other_vaults_remain_searchable(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "vaults/projects/demo-app/runbooks/pipeline-timeout.md",
        "---\ntitle: Pipeline timeout QA\ntags: [pipeline, timeout]\n---\nHandle pipeline timeout in QA.\n",
    )
    _write(
        tmp_path,
        "vaults/projects/demo-platform/runbooks/pipeline-timeout.md",
        "---\ntitle: Pipeline timeout platform\ntags: [pipeline]\n---\nGeneral pipeline timeout recovery.\n",
    )
    index = SearchIndex(tmp_path, tmp_path / ".vaultin-runtime" / "search.db")
    index.rebuild()
    hits = index.search("pipeline timeout", current_project="demo-app", limit=10)
    assert hits[0].project == "demo-app"
    assert any(hit.project == "demo-platform" for hit in hits)


def test_index_can_be_deleted_and_rebuilt(tmp_path: Path) -> None:
    _write(tmp_path, "knowledge/appsec/sast.md", "# SAST\nStatic analysis guidance.\n")
    db = tmp_path / ".vaultin-runtime" / "search.db"
    index = SearchIndex(tmp_path, db)
    index.rebuild()
    assert index.search("Static analysis")
    db.unlink()
    index = SearchIndex(tmp_path, db)
    index.rebuild()
    assert index.search("Static analysis")
