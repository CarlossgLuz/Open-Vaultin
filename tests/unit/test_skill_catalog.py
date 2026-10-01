from pathlib import Path

import pytest

from vaultin.skills.catalog import SkillCatalog, SkillCatalogError


def _skill(root: Path, dirname: str, name: str) -> None:
    path = root / ".agents/skills" / dirname
    path.mkdir(parents=True, exist_ok=True)
    path.joinpath("SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Test skill {name}\n---\n# {name}\n",
        encoding="utf-8",
    )


def test_catalog_loads_skill_md_frontmatter(tmp_path: Path) -> None:
    _skill(tmp_path, "python", "python")
    catalog = SkillCatalog.load(tmp_path)
    assert catalog.names() == ["python"]


def test_duplicate_skill_names_fail(tmp_path: Path) -> None:
    _skill(tmp_path, "python-one", "python")
    _skill(tmp_path, "python-two", "python")
    with pytest.raises(SkillCatalogError, match="duplicate skill name"):
        SkillCatalog.load(tmp_path)
