from pathlib import Path
import pytest

from vaultin.config import load_settings
from vaultin.errors import ConfigError
from vaultin.paths import VaultinPaths


def test_load_settings_requires_valid_canonical_config(tmp_path: Path) -> None:
    (tmp_path / "vaultin.yaml").write_text(
        "version: 1\nrepository: acme/Vaultin\nproject_vault_owner: acme\n",
        encoding="utf-8",
    )
    settings = load_settings(tmp_path)
    assert settings.repository == "acme/Vaultin"
    assert settings.project_vault_owner == "acme"
    assert settings.fail_closed is True


def test_corrupted_yaml_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "vaultin.yaml").write_text("version: [", encoding="utf-8")
    with pytest.raises(ConfigError, match="invalid vaultin.yaml"):
        load_settings(tmp_path)


def test_missing_config_does_not_invent_defaults(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="vaultin.yaml not found"):
        load_settings(tmp_path)


def test_runtime_directory_name_is_honored(tmp_path: Path) -> None:
    (tmp_path / "vaultin.yaml").write_text(
        "version: 1\n"
        "repository: acme/vaultin\n"
        "project_vault_owner: acme\n"
        "runtime_dir_name: .custom-vaultin-runtime\n",
        encoding="utf-8",
    )

    paths = VaultinPaths.from_root(tmp_path)

    assert paths.runtime == tmp_path.resolve() / ".custom-vaultin-runtime"
    assert paths.ledger_db == paths.runtime / "vaultin.db"


def test_project_vault_owner_is_required(tmp_path: Path) -> None:
    (tmp_path / "vaultin.yaml").write_text(
        "version: 1\nrepository: acme/Vaultin\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="invalid vaultin.yaml"):
        load_settings(tmp_path)
