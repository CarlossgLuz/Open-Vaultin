from pathlib import Path

import pytest

from vaultin.mcp.server import VaultinMCPService


def _system(tmp_path: Path) -> VaultinMCPService:
    (tmp_path / "vaults/projects/demo/runbooks").mkdir(parents=True)
    (tmp_path / "knowledge").mkdir()
    (tmp_path / "vaults/registry.yaml").write_text("version: 1\nprojects: {}\n", encoding="utf-8")
    return VaultinMCPService(tmp_path)


def test_mcp_write_targets_canonical_vault_only(tmp_path: Path) -> None:
    service = _system(tmp_path)
    result = service.write_project_note("demo", "runbooks/demo.md", "# Demo\n")
    assert result["path"] == "vaults/projects/demo/runbooks/demo.md"
    assert (tmp_path / "vaults/projects/demo/runbooks/demo.md").is_file()
    assert not (tmp_path.parent / "vault-demo/runbooks/demo.md").exists()


def test_mcp_write_rejects_path_escape(tmp_path: Path) -> None:
    service = _system(tmp_path)
    with pytest.raises(ValueError, match="invalid relative path"):
        service.write_project_note("demo", "../../outside.md", "bad")


def test_mcp_search_reads_canonical_knowledge(tmp_path: Path) -> None:
    service = _system(tmp_path)
    (tmp_path / "knowledge/appsec.md").write_text("# AppSec\nSecure pipeline validation\n", encoding="utf-8")
    service.rebuild_index()
    hits = service.search_knowledge("pipeline validation")
    assert hits[0]["path"] == "knowledge/appsec.md"
