from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError
import yaml


class SkillCatalogError(RuntimeError):
    pass


class SkillMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    description: str
    path: str | None = None


class SkillCatalog:
    def __init__(self, skills: list[SkillMetadata]) -> None:
        by_name: dict[str, SkillMetadata] = {}
        for skill in skills:
            if skill.name in by_name:
                raise SkillCatalogError(f"duplicate skill name: {skill.name}")
            by_name[skill.name] = skill
        self._skills = by_name

    @classmethod
    def from_skills(cls, skills: list[SkillMetadata]) -> "SkillCatalog":
        return cls(skills)

    @staticmethod
    def _frontmatter(text: str) -> dict[str, object]:
        if not text.startswith("---\n"):
            raise SkillCatalogError("SKILL.md missing YAML frontmatter")
        end = text.find("\n---\n", 4)
        if end == -1:
            raise SkillCatalogError("SKILL.md has unterminated YAML frontmatter")
        try:
            raw = yaml.safe_load(text[4:end]) or {}
        except yaml.YAMLError as exc:
            raise SkillCatalogError(f"invalid SKILL.md frontmatter: {exc}") from exc
        if not isinstance(raw, dict):
            raise SkillCatalogError("SKILL.md frontmatter must be a mapping")
        return raw

    @classmethod
    def load(cls, root: Path) -> "SkillCatalog":
        root = Path(root)
        base = root / ".agents" / "skills"
        if not base.is_dir():
            return cls([])
        skills: list[SkillMetadata] = []
        for path in sorted(base.glob("*/SKILL.md")):
            raw = cls._frontmatter(path.read_text(encoding="utf-8"))
            try:
                skill = SkillMetadata.model_validate({**raw, "path": path.relative_to(root).as_posix()})
            except ValidationError as exc:
                raise SkillCatalogError(f"invalid skill metadata in {path}: {exc}") from exc
            skills.append(skill)
        return cls(skills)

    def names(self) -> list[str]:
        return sorted(self._skills)

    def get(self, name: str) -> SkillMetadata:
        try:
            return self._skills[name]
        except KeyError as exc:
            raise SkillCatalogError(f"unknown skill: {name}") from exc
