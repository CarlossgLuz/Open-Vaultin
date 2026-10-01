from __future__ import annotations

import argparse
import json
import re
import os
import shlex
import tomllib
from pathlib import Path
from typing import Any

from filelock import FileLock


def ensure_personal_marketplace(home: Path) -> Path:
    home = Path(home).expanduser().resolve()
    path = home / ".agents" / "plugins" / "marketplace.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(path) + ".lock")

    with lock:
        if path.is_file():
            try:
                raw: Any = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid personal marketplace JSON: {exc}") from exc
            if not isinstance(raw, dict):
                raise RuntimeError("personal marketplace must be a JSON object")
            data = dict(raw)
        else:
            data = {
                "name": "vaultin-personal",
                "interface": {"displayName": "Vaultin Personal"},
                "plugins": [],
            }

        plugins = data.get("plugins", [])
        if not isinstance(plugins, list):
            raise RuntimeError("personal marketplace plugins must be a list")

        retained = [
            item
            for item in plugins
            if not (isinstance(item, dict) and item.get("name") == "vaultin")
        ]
        retained.append(
            {
                "name": "vaultin",
                "source": {
                    "source": "local",
                    "path": "./.codex/plugins/vaultin",
                },
                "policy": {
                    "installation": "INSTALLED_BY_DEFAULT",
                    "authentication": "ON_INSTALL",
                },
                "category": "Productivity",
            }
        )

        data["plugins"] = retained
        data.setdefault("name", "vaultin-personal")
        data.setdefault("interface", {"displayName": "Vaultin Personal"})

        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    return path


def ensure_user_plugin_enabled(home: Path, marketplace_name: str) -> Path:
    home = Path(home).expanduser().resolve()
    marketplace_name = marketplace_name.strip()
    if not marketplace_name or any(ch in marketplace_name for ch in ['"', "\n", "\r"]):
        raise ValueError("invalid marketplace name")

    path = home / ".codex" / "config.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(path) + ".lock")

    plugin_key = f"vaultin@{marketplace_name}"
    section_header = f'[plugins."{plugin_key}"]'
    section_pattern = re.compile(
        rf'(?ms)^\[plugins\."{re.escape(plugin_key)}"\][^\n]*\n'
        rf'.*?(?=^\[|\Z)'
    )

    with lock:
        original = path.read_text(encoding="utf-8") if path.is_file() else ""
        text = original.replace("\r\n", "\n")

        # Repair malformed boundaries created by older Vaultin installers.
        text = re.sub(
            r'(?m)^(\s*enabled\s*=\s*(?:true|false))(?=\[[A-Za-z0-9_.\"\'-]+\])',
            r'\1\n\n',
            text,
        )

        canonical = f"{section_header}\nenabled = true\n\n"
        if section_pattern.search(text):
            text = section_pattern.sub(canonical, text, count=1)
        else:
            if text and not text.endswith("\n"):
                text += "\n"
            if text and not text.endswith("\n\n"):
                text += "\n"
            text += canonical

        try:
            tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            raise RuntimeError(
                f"config.toml remains invalid after Vaultin repair: {exc}"
            ) from exc

        temporary = path.with_suffix(".toml.tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(path)

    return path


def _hook_command_prefix(hook_command: Path, *, platform_name: str | None = None) -> str:
    raw = str(Path(hook_command).resolve())
    platform = platform_name or os.name
    if platform == "nt":
        # Codex currently passes hook commands through cmd.exe /C on Windows.
        # Quoted executable paths are re-escaped by the runner and fail with exit code 1.
        if any(char.isspace() for char in raw):
            raise RuntimeError(
                "Vaultin hook path contains whitespace; current Codex Windows hook runner "
                "cannot safely execute quoted hook paths"
            )
        return raw
    return shlex.quote(raw)


def ensure_user_hooks(home: Path, *, template_path: Path, hook_command: Path) -> Path:
    home = Path(home).expanduser().resolve()
    template_path = Path(template_path).resolve()
    hook_command = Path(hook_command).resolve()

    if not template_path.is_file():
        raise FileNotFoundError(f"hook template not found: {template_path}")

    path = home / ".codex" / "hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(path) + ".lock")

    with lock:
        current: dict[str, Any]
        if path.is_file():
            raw = path.read_text(encoding="utf-8")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                from datetime import UTC, datetime

                stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
                backup = path.with_name(f"hooks.json.invalid-{stamp}.bak")
                backup.write_text(raw, encoding="utf-8")
                current = {"description": "User lifecycle hooks", "hooks": {}}
            else:
                if not isinstance(parsed, dict):
                    raise RuntimeError("existing hooks.json must contain a JSON object")
                current = dict(parsed)
        else:
            current = {"description": "User lifecycle hooks", "hooks": {}}

        current_hooks = current.setdefault("hooks", {})
        if not isinstance(current_hooks, dict):
            raise RuntimeError("existing hooks.json field 'hooks' must be an object")

        template = json.loads(template_path.read_text(encoding="utf-8"))
        template_hooks = template.get("hooks", {})
        if not isinstance(template_hooks, dict):
            raise RuntimeError("Vaultin hook template field 'hooks' must be an object")

        marker = "vaultinctl-hook"
        for event, groups in list(current_hooks.items()):
            if not isinstance(groups, list):
                continue
            retained = []
            for group in groups:
                if not isinstance(group, dict):
                    retained.append(group)
                    continue
                handlers = group.get("hooks", [])
                contains_vaultin = any(
                    isinstance(handler, dict)
                    and marker in str(handler.get("command", ""))
                    for handler in handlers
                )
                if not contains_vaultin:
                    retained.append(group)
            current_hooks[event] = retained

        command_prefix = _hook_command_prefix(hook_command)
        for event, groups in template_hooks.items():
            rendered_groups = json.loads(json.dumps(groups))
            for group in rendered_groups:
                for handler in group.get("hooks", []):
                    if handler.get("type") != "command":
                        continue
                    original = str(handler.get("command", "")).strip()
                    parts = original.split(maxsplit=1)
                    suffix = parts[1] if len(parts) == 2 else ""
                    handler["command"] = command_prefix + (f" {suffix}" if suffix else "")
            current_hooks.setdefault(event, []).extend(rendered_groups)

        encoded = json.dumps(current, indent=2, ensure_ascii=False) + "\n"
        json.loads(encoded)

        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(encoded, encoding="utf-8")
        temporary.replace(path)

    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--hooks-template", type=Path)
    parser.add_argument("--hook-command", type=Path)
    args = parser.parse_args(argv)

    marketplace_path = ensure_personal_marketplace(args.home)
    data = json.loads(marketplace_path.read_text(encoding="utf-8"))
    marketplace_name = str(data["name"])
    config_path = ensure_user_plugin_enabled(args.home, marketplace_name)
    hooks_path = None
    if args.hooks_template or args.hook_command:
        if not args.hooks_template or not args.hook_command:
            raise ValueError("--hooks-template and --hook-command must be provided together")
        hooks_path = ensure_user_hooks(
            args.home,
            template_path=args.hooks_template,
            hook_command=args.hook_command,
        )

    print(marketplace_path)
    print(config_path)
    if hooks_path is not None:
        print(hooks_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
