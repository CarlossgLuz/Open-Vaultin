from pathlib import Path


def test_install_scripts_exist_and_reference_healthcheck() -> None:
    root = Path.cwd()
    ps1 = (root / "scripts/install.ps1").read_text(encoding="utf-8")
    sh = (root / "scripts/install.sh").read_text(encoding="utf-8")
    assert "vaultinctl health" in ps1
    assert "vaultinctl health" in sh
    assert "Python 3.11" in ps1
    assert "Python 3.11" in sh


def test_codex_plugin_manifest_registers_lifecycle_hooks() -> None:
    root = Path.cwd()
    hooks = (root / "adapters/codex-plugin/hooks/hooks.json").read_text(encoding="utf-8")
    for event in ["SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop", "Interrupt"]:
        assert event in hooks


def test_personal_marketplace_registration_preserves_existing_plugins(tmp_path: Path) -> None:
    import json
    from vaultin.adapters.codex_install import ensure_personal_marketplace

    marketplace = tmp_path / ".agents/plugins/marketplace.json"
    marketplace.parent.mkdir(parents=True)
    marketplace.write_text(json.dumps({
        "name": "personal",
        "plugins": [
            {
                "name": "existing",
                "source": {"source": "local", "path": "./existing"}
            }
        ]
    }), encoding="utf-8")

    result = ensure_personal_marketplace(tmp_path)
    data = json.loads(result.read_text(encoding="utf-8"))
    names = [item["name"] for item in data["plugins"]]
    assert names == ["existing", "vaultin"]
    vaultin = data["plugins"][1]
    assert vaultin["source"]["path"] == "./.codex/plugins/vaultin"


def test_install_docs_require_one_time_hook_trust_review() -> None:
    root = Path.cwd()
    install = (root / "docs/operations/install.md").read_text(encoding="utf-8").casefold()
    assert "marketplace.json" in install
    assert "trust" in install
    assert "uma vez" in install or "one-time" in install


def test_windows_installer_exposes_vaultinctl_and_registers_marketplace() -> None:
    root = Path.cwd()
    ps1 = (root / "scripts/install.ps1").read_text(encoding="utf-8")
    assert "vaultinctl.cmd" in ps1
    assert "[Environment]::SetEnvironmentVariable" in ps1
    assert "$env:Path" in ps1
    assert "vaultin.adapters.codex_install" in ps1


def test_linux_installer_registers_personal_marketplace() -> None:
    root = Path.cwd()
    sh = (root / "scripts/install.sh").read_text(encoding="utf-8")
    assert "vaultin.adapters.codex_install" in sh


def test_codex_compat_manifest_declares_hooks() -> None:
    import json

    root = Path.cwd()
    portable = json.loads((root / "adapters/codex-plugin/plugin.json").read_text(encoding="utf-8"))
    compat = json.loads((root / "adapters/codex-plugin/.codex-plugin/plugin.json").read_text(encoding="utf-8"))

    assert portable["extensions"]["com.openai"]["hooks"] == []
    assert compat["name"] == "vaultin"
    assert compat["hooks"] == []
    assert (root / "adapters/codex-plugin/hooks/hooks.json").is_file()


def test_installers_invalidate_only_vaultin_plugin_cache() -> None:
    root = Path.cwd()
    ps1 = (root / "scripts/install.ps1").read_text(encoding="utf-8")
    sh = (root / "scripts/install.sh").read_text(encoding="utf-8")

    assert "plugins\\cache\\vaultin-personal\\vaultin" in ps1
    assert "plugins/cache/vaultin-personal/vaultin" in sh


def test_user_codex_config_enables_local_vaultin_plugin_without_clobbering(tmp_path: Path) -> None:
    from vaultin.adapters.codex_install import ensure_user_plugin_enabled

    config = tmp_path / ".codex" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text('model = "gpt-5.6"\n\n[features]\nplugin_sharing = true\n', encoding="utf-8")

    result = ensure_user_plugin_enabled(tmp_path, "vaultin-personal")
    text = result.read_text(encoding="utf-8")

    assert 'model = "gpt-5.6"' in text
    assert '[features]' in text
    assert '[plugins."vaultin@vaultin-personal"]' in text
    assert 'enabled = true' in text


def test_user_codex_config_flips_existing_vaultin_plugin_to_enabled(tmp_path: Path) -> None:
    from vaultin.adapters.codex_install import ensure_user_plugin_enabled

    config = tmp_path / ".codex" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        '[plugins."vaultin@vaultin-personal"]\nenabled = false\n',
        encoding="utf-8",
    )

    ensure_user_plugin_enabled(tmp_path, "vaultin-personal")
    text = config.read_text(encoding="utf-8")

    assert '[plugins."vaultin@vaultin-personal"]' in text
    assert 'enabled = true' in text
    assert 'enabled = false' not in text


def test_windows_installer_stops_on_native_failures() -> None:
    root = Path.cwd()
    ps1 = (root / "scripts/install.ps1").read_text(encoding="utf-8")
    assert "Invoke-NativeChecked" in ps1
    assert "$LASTEXITCODE" in ps1


def test_windows_installer_uses_delimited_lastexitcode() -> None:
    root = Path.cwd()
    ps1 = (root / "scripts/install.ps1").read_text(encoding="utf-8")
    assert "${LASTEXITCODE}:" in ps1
    assert "$LASTEXITCODE:" not in ps1


def test_user_codex_config_repairs_glued_section_header(tmp_path: Path) -> None:
    import tomllib
    from vaultin.adapters.codex_install import ensure_user_plugin_enabled

    config = tmp_path / ".codex" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        '[plugins."vaultin@vaultin-personal"]\nenabled = true[desktop]\n'
        'followUpQueueMode = "steer"\n',
        encoding="utf-8",
    )

    ensure_user_plugin_enabled(tmp_path, "vaultin-personal")
    text = config.read_text(encoding="utf-8")
    parsed = tomllib.loads(text)

    assert parsed["plugins"]["vaultin@vaultin-personal"]["enabled"] is True
    assert parsed["desktop"]["followUpQueueMode"] == "steer"
    assert "enabled = true[desktop]" not in text


def test_user_codex_config_refuses_to_write_invalid_toml(tmp_path: Path) -> None:
    import pytest
    from vaultin.adapters.codex_install import ensure_user_plugin_enabled

    config = tmp_path / ".codex" / "config.toml"
    config.parent.mkdir(parents=True)
    original = '[broken\nvalue = true\n'
    config.write_text(original, encoding="utf-8")

    with pytest.raises(RuntimeError, match="config.toml remains invalid"):
        ensure_user_plugin_enabled(tmp_path, "vaultin-personal")

    assert config.read_text(encoding="utf-8") == original


def test_user_hooks_merge_preserves_non_vaultin_hooks(tmp_path: Path) -> None:
    import json
    from vaultin.adapters.codex_install import ensure_user_hooks

    hooks_path = tmp_path / ".codex" / "hooks.json"
    hooks_path.parent.mkdir(parents=True)
    hooks_path.write_text(json.dumps({
        "description": "Existing hooks",
        "hooks": {
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python existing.py"
                        }
                    ]
                }
            ]
        }
    }), encoding="utf-8")

    result = ensure_user_hooks(
        tmp_path,
        template_path=Path.cwd() / "adapters/codex-plugin/hooks/hooks.json",
        hook_command=tmp_path / ".vaultin/bin/vaultinctl-hook.cmd",
    )
    data = json.loads(result.read_text(encoding="utf-8"))
    commands = [
        hook["command"]
        for group in data["hooks"]["SessionStart"]
        for hook in group["hooks"]
    ]
    assert "python existing.py" in commands
    assert any("vaultinctl-hook.cmd" in command and "session-start" in command for command in commands)


def test_user_hooks_reinstall_is_idempotent(tmp_path: Path) -> None:
    import json
    from vaultin.adapters.codex_install import ensure_user_hooks

    template = Path.cwd() / "adapters/codex-plugin/hooks/hooks.json"
    wrapper = tmp_path / ".vaultin/bin/vaultinctl-hook.cmd"

    ensure_user_hooks(tmp_path, template_path=template, hook_command=wrapper)
    ensure_user_hooks(tmp_path, template_path=template, hook_command=wrapper)

    data = json.loads((tmp_path / ".codex/hooks.json").read_text(encoding="utf-8"))
    for event in ["SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop", "SessionEnd"]:
        vaultin = [
            hook["command"]
            for group in data["hooks"][event]
            for hook in group["hooks"]
            if "vaultinctl-hook" in hook.get("command", "")
        ]
        assert len(vaultin) == 1


def test_user_hooks_back_up_invalid_existing_json(tmp_path: Path) -> None:
    from vaultin.adapters.codex_install import ensure_user_hooks

    path = tmp_path / ".codex/hooks.json"
    path.parent.mkdir(parents=True)
    path.write_text("not-json", encoding="utf-8")

    result = ensure_user_hooks(
        tmp_path,
        template_path=Path.cwd() / "adapters/codex-plugin/hooks/hooks.json",
        hook_command=tmp_path / ".vaultin/bin/vaultinctl-hook.cmd",
    )

    assert result.is_file()
    backups = list(path.parent.glob("hooks.json.invalid-*.bak"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "not-json"


def test_installers_register_user_level_hooks() -> None:
    root = Path.cwd()
    ps1 = (root / "scripts/install.ps1").read_text(encoding="utf-8")
    sh = (root / "scripts/install.sh").read_text(encoding="utf-8")
    assert "--hook-command" in ps1
    assert "--hooks-template" in ps1
    assert "--hook-command" in sh
    assert "--hooks-template" in sh


def test_windows_installer_writes_bomless_root_and_pins_hook_root() -> None:
    root = Path.cwd()
    ps1 = (root / "scripts/install.ps1").read_text(encoding="utf-8")
    assert "UTF8Encoding($false)" in ps1
    assert '-m vaultin.hooks.entrypoint %* --root' in ps1


def test_windows_hook_command_prefix_is_unquoted(tmp_path: Path) -> None:
    from vaultin.adapters.codex_install import _hook_command_prefix

    hook = tmp_path / "vaultinctl-hook.cmd"
    hook.write_text("@echo off\n", encoding="utf-8")
    rendered = _hook_command_prefix(hook, platform_name="nt")

    assert rendered == str(hook.resolve())
    assert '"' not in rendered


def test_windows_hook_command_rejects_whitespace_path(tmp_path: Path) -> None:
    import pytest
    from vaultin.adapters.codex_install import _hook_command_prefix

    hook = tmp_path / "path with spaces" / "vaultinctl-hook.cmd"
    hook.parent.mkdir()
    hook.write_text("@echo off\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="contains whitespace"):
        _hook_command_prefix(hook, platform_name="nt")


def test_hook_runtime_is_latency_bounded_and_context_capped() -> None:
    import json

    root = Path.cwd()
    data = json.loads((root / "adapters/codex-plugin/hooks/hooks.json").read_text(encoding="utf-8"))
    hooks = data["hooks"]

    session = hooks["SessionStart"][0]["hooks"][0]
    prompt = hooks["UserPromptSubmit"][0]["hooks"][0]
    pre_tool = hooks["PreToolUse"][0]["hooks"][0]
    post_tool = hooks["PostToolUse"][0]["hooks"][0]
    stop = hooks["Stop"][0]["hooks"][0]
    interrupt = hooks["Interrupt"][0]["hooks"][0]

    assert session["additionalContextLimit"] <= 128
    assert prompt["additionalContextLimit"] <= 128
    assert pre_tool["timeout"] <= 5
    assert post_tool["async"] is True
    assert stop["timeout"] <= 15
    assert interrupt["timeout"] <= 3


def test_installers_use_editable_checkout_install() -> None:
    root = Path.cwd()
    ps1 = (root / "scripts/install.ps1").read_text(encoding="utf-8")
    sh = (root / "scripts/install.sh").read_text(encoding="utf-8")

    assert "pip install --editable $Root" in ps1
    assert 'pip install --editable "$ROOT"' in sh


def test_hook_wrappers_force_live_checkout_source() -> None:
    root = Path.cwd()
    ps1 = (root / "scripts/install.ps1").read_text(encoding="utf-8")
    sh = (root / "scripts/install.sh").read_text(encoding="utf-8")

    assert 'set `"PYTHONPATH=$Root;%PYTHONPATH%`"' in ps1
    assert '-m vaultin.hooks.entrypoint %* --root' in ps1
    assert '-m vaultin.cli %*' in ps1

    assert 'export PYTHONPATH="$ROOT' in sh
    assert '-m vaultin.hooks.entrypoint "\$@" --root "$ROOT"' in sh
    assert '-m vaultin.cli "\$@"' in sh
