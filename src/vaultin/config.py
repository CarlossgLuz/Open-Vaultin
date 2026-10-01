from pathlib import Path

import yaml
from pydantic import ValidationError

from vaultin.errors import ConfigError
from vaultin.models import VaultinSettings


def load_settings(root: Path) -> VaultinSettings:
    path = root / "vaultin.yaml"
    if not path.is_file():
        raise ConfigError("vaultin.yaml not found")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return VaultinSettings.model_validate(raw)
    except (yaml.YAMLError, ValidationError, TypeError) as exc:
        raise ConfigError(f"invalid vaultin.yaml: {exc}") from exc
