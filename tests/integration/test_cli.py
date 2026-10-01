from pathlib import Path

from typer.testing import CliRunner

from vaultin.cli import app


runner = CliRunner()


def test_health_command_returns_nonzero_on_invalid_config(tmp_path: Path) -> None:
    (tmp_path / "vaultin.yaml").write_text("version: [", encoding="utf-8")
    result = runner.invoke(app, ["health", "--root", str(tmp_path)])
    assert result.exit_code != 0
    assert "BLOCKED" in result.stdout


def test_health_command_passes_on_minimal_valid_repository(tmp_path: Path) -> None:
    (tmp_path / "vaultin.yaml").write_text(
        "version: 1\nrepository: acme/Vaultin\nproject_vault_owner: acme\n",
        encoding="utf-8",
    )
    (tmp_path / "policies").mkdir()
    (tmp_path / "policies/core.yaml").write_text("critical: {}\nproject: {}\n", encoding="utf-8")
    (tmp_path / "workflows").mkdir()
    source = Path.cwd() / "workflows/state-machine.yaml"
    (tmp_path / "workflows/state-machine.yaml").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "agents/profiles").mkdir(parents=True)
    (tmp_path / "agents/registry.yaml").write_text("version: 1\nagents: []\n", encoding="utf-8")
    result = runner.invoke(app, ["health", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "PASS" in result.stdout
