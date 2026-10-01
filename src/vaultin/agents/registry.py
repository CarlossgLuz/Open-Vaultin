from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError
import yaml


class AgentRegistryError(RuntimeError):
    pass


class AgentProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    role: str
    preferred_skills: list[str] = Field(default_factory=list)
    description: str = ""


class AgentRegistry:
    def __init__(self, profiles: list[AgentProfile], profile_paths: dict[str, Path] | None = None) -> None:
        self._profiles = {profile.name: profile for profile in profiles}
        self._profile_paths = profile_paths or {}
        if len(self._profiles) != len(profiles):
            raise AgentRegistryError("duplicate agent name")

    @classmethod
    def from_profiles(cls, profiles: list[AgentProfile]) -> "AgentRegistry":
        return cls(profiles)

    @classmethod
    def load(cls, root: Path) -> "AgentRegistry":
        root = Path(root)
        registry_path = root / "agents" / "registry.yaml"
        if not registry_path.is_file():
            raise AgentRegistryError("agents/registry.yaml not found")
        try:
            raw = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise AgentRegistryError(f"invalid agent registry YAML: {exc}") from exc
        items = raw.get("agents", [])
        if not isinstance(items, list):
            raise AgentRegistryError("agents registry field must be a list")
        profiles: list[AgentProfile] = []
        paths: dict[str, Path] = {}
        for item in items:
            if not isinstance(item, dict) or not item.get("name") or not item.get("profile"):
                raise AgentRegistryError("invalid agent registry entry")
            name = str(item["name"])
            profile_path = root / str(item["profile"])
            if not profile_path.is_file():
                raise AgentRegistryError(f"missing profile for {name}: {profile_path}")
            try:
                profile_raw = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
                profile = AgentProfile.model_validate(profile_raw)
            except (yaml.YAMLError, ValidationError) as exc:
                raise AgentRegistryError(f"invalid profile for {name}: {exc}") from exc
            if profile.name != name:
                raise AgentRegistryError(f"profile name mismatch for {name}: {profile.name}")
            profiles.append(profile)
            paths[name] = profile_path
        registry = cls(profiles, paths)

        from vaultin.skills.catalog import SkillCatalog, SkillCatalogError

        try:
            catalog = SkillCatalog.load(root)
        except SkillCatalogError as exc:
            raise AgentRegistryError(str(exc)) from exc
        known = set(catalog.names())
        unknown = sorted(
            {skill for profile in profiles for skill in profile.preferred_skills if skill not in known}
        )
        if unknown:
            raise AgentRegistryError(f"unknown preferred skill(s): {', '.join(unknown)}")
        return registry

    def names(self) -> list[str]:
        return sorted(self._profiles)

    def get(self, name: str) -> AgentProfile:
        try:
            return self._profiles[name]
        except KeyError as exc:
            raise AgentRegistryError(f"unknown agent: {name}") from exc

    def missing_profiles(self) -> list[str]:
        return sorted(name for name, path in self._profile_paths.items() if not path.is_file())
