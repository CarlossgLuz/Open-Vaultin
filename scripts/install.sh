#!/usr/bin/env bash
# Final installer gate: vaultinctl health must pass before installation is considered successful.
set -euo pipefail

# Vaultin requires Python 3.11+.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
PYTHON="${PYTHON:-python3}"
"$PYTHON" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Vaultin requires Python 3.11 or newer")
PY

STATE="$HOME/.vaultin"
VENV="$STATE/venv"
BIN="$STATE/bin"
mkdir -p "$STATE" "$BIN" "$HOME/.local/bin" "$HOME/.codex/plugins"
printf '%s\n' "$ROOT" > "$STATE/root"
"$PYTHON" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install --editable "$ROOT"

cat > "$BIN/vaultinctl" <<EOF
#!/usr/bin/env bash
export PYTHONPATH="$ROOT\${PYTHONPATH:+:\$PYTHONPATH}"
exec "$VENV/bin/python" -m vaultin.cli "\$@"
EOF
chmod +x "$BIN/vaultinctl"
ln -sf "$BIN/vaultinctl" "$HOME/.local/bin/vaultinctl"

cat > "$BIN/vaultinctl-hook" <<EOF
#!/usr/bin/env bash
export PYTHONPATH="$ROOT\${PYTHONPATH:+:\$PYTHONPATH}"
exec "$VENV/bin/python" -m vaultin.hooks.entrypoint "\$@" --root "$ROOT"
EOF
chmod +x "$BIN/vaultinctl-hook"

rm -rf "$HOME/.codex/plugins/vaultin"
rm -rf "$HOME/.codex/plugins/cache/vaultin-personal/vaultin"
cp -R "$ROOT/adapters/codex-plugin" "$HOME/.codex/plugins/vaultin"
"$VENV/bin/python" -m vaultin.adapters.codex_install --home "$HOME" --hooks-template "$ROOT/adapters/codex-plugin/hooks/hooks.json" --hook-command "$BIN/vaultinctl-hook"
export VAULTIN_HOOK_COMMAND="$BIN/vaultinctl-hook"
"$VENV/bin/python" - <<'PY'
import json
import os
from pathlib import Path
import shlex

path = Path.home() / ".codex" / "plugins" / "vaultin" / "hooks" / "hooks.json"
data = json.loads(path.read_text(encoding="utf-8"))
command = shlex.quote(os.environ["VAULTIN_HOOK_COMMAND"])
for matchers in data.get("hooks", {}).values():
    for matcher in matchers:
        for hook in matcher.get("hooks", []):
            if hook.get("type") == "command":
                original = str(hook.get("command", "")).strip()
                parts = original.split(maxsplit=1)
                suffix = parts[1] if len(parts) == 2 else ""
                hook["command"] = command + ((" " + suffix) if suffix else "")
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

"$BIN/vaultinctl" health --root "$ROOT"
printf 'Vaultin installed. Codex hook uses the absolute wrapper at %s; no PATH change is required for governance.\n' "$BIN/vaultinctl-hook"
