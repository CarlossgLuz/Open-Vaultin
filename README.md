# Open-Vaultin

**Language:** **English** | [Português (Brasil)](README.pt-BR.md)

[![CI](https://github.com/CarlossgLuz/Open-Vaultin/actions/workflows/ci.yml/badge.svg)](https://github.com/CarlossgLuz/Open-Vaultin/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Early V1](https://img.shields.io/badge/status-early%20V1-orange.svg)](CHANGELOG.md)

**Open-Vaultin** is the open-source distribution of Vaultin: a local-first governance and durable-knowledge layer for AI-assisted software engineering.

Vaultin provides a shared and auditable control plane for **agents, skills, policies, routing, execution lifecycle, project knowledge, evidence and Git-backed synchronization**.

The goal is simple: keep AI-assisted development organized, traceable and consistent without requiring Vaultin-specific files inside every source repository.

> **Status:** early V1 / pre-1.0. The core runtime is implemented and validated on Windows and Linux. Client integrations should still be validated in the environment where Vaultin is installed.

---

## What does Vaultin solve?

AI coding environments easily accumulate fragmented state:

- each AI client may receive different context;
- useful knowledge is lost between sessions;
- agents and skills can drift over time;
- interrupted executions can leave stale state behind;
- routing decisions can become mixed with authorization rules;
- generated changes are difficult to audit;
- synchronization failures can go unnoticed.

Vaultin separates those concerns and gives them one canonical home.

---

## How it works

```text
User task
   │
   ▼
AI client / adapter
   │
   ▼
Vaultin lifecycle
   │
   ├── project discovery
   ├── policy loading
   ├── agent + skill registry
   └── durable execution ledger
   │
   ▼
Routing
   │
   ├── JEV / TypeSafe System One (optional)
   └── deterministic fallback
   │
   ▼
Governed execution
   │
   ├── lifecycle hooks
   ├── policy checks
   ├── validation evidence
   └── knowledge curation
   │
   ▼
Git + project-vault synchronization
   │
   ▼
Evidence-backed final state
```

**JEV is advisory. Policy remains authoritative.**

In practice, Vaultin sits between the AI client and the governed execution lifecycle. It helps decide what context should be used, records execution state and keeps durable project knowledge synchronized.

---

## Main capabilities

- local-first execution ledger;
- Codex lifecycle integration;
- orphaned execution recovery;
- bounded hook latency;
- compact routing context to reduce unnecessary model tokens;
- typed JEV routing with deterministic fallback;
- strict policy precedence;
- agent and skill registries;
- canonical project knowledge;
- project-vault synchronization with divergence protection;
- narrow MCP interface for secondary AI clients;
- Windows and Linux installers;
- evidence-backed execution receipts;
- explicit degraded/failure states;
- cross-platform CI.

---

## Recommended usage

For testing, you can clone this repository directly.

For regular personal use, create an **independent private repository** containing a copy of Open-Vaultin. GitHub forks of public repositories are public; do not use a public fork for private project knowledge.

Your private copy can accumulate your own:

- project vaults;
- knowledge;
- operational configuration;
- execution history;
- local integrations.

Do **not** publish:

- API keys or access tokens;
- passwords or credentials;
- private repository names;
- local filesystem paths containing sensitive information;
- proprietary project knowledge;
- private prompts or execution history that should not be public.

---

## Requirements

Before installing Vaultin, make sure you have:

- Python **3.11+**
- Git
- Windows or Linux
- a compatible Codex/ChatGPT surface for lifecycle hooks

Optional:

- `TYPESAFE_API_KEY` if you want to enable JEV / TypeSafe routing

You can verify Python and Git with:

```bash
python --version
git --version
```

On Windows, depending on your Python installation, you may need:

```powershell
py --version
```

---

# Install and integrate, step by step

Follow these steps on **the computer and OS account that runs Codex**. A Windows install does not configure WSL, a remote VM, a container or a browser-hosted environment. Install separately inside the environment where the client executes hooks.

This guide uses `octocat/Vaultin-Personal` as an example. Replace `octocat` with your GitHub username and `Vaultin-Personal` with your chosen repository name. Never paste the example API keys literally.

## 1. Prepare your tools and private copy

Check Python 3.11+, Git and your installed Codex client. On Linux use `python3 --version`; on Windows use `python --version`. If Windows only exposes `py`, set `$env:PYTHON = "py"` before running the installer.

```text
git --version
```

If using Codex CLI, also check `codex --version` and finish its own authentication first. Vaultin does not install Codex or sign you in. Hook support depends on the client/version; writing configuration files alone does not prove the client runs them.

For a local evaluation only:

```bash
git clone https://github.com/CarlossgLuz/Open-Vaultin.git
cd Open-Vaultin
```

For personal use with private knowledge:

1. In GitHub, create a new repository such as `Vaultin-Personal`, select **Private**, and leave it empty (no generated README, license or `.gitignore`).
2. Clone Open-Vaultin to a stable local directory, then point `origin` at your new repository:

```bash
git clone https://github.com/CarlossgLuz/Open-Vaultin.git Vaultin-Personal
cd Vaultin-Personal
git remote rename origin upstream
git remote add origin https://github.com/octocat/Vaultin-Personal.git
git remote -v
git push -u origin main
```

These commands work in PowerShell and Bash. Authenticate using your Git credential manager or SSH setup when Git requires it. Keep the MIT license. `origin` must be your private repository; `upstream` is the public source for future updates. See GitHub's [repository duplication guide](https://docs.github.com/en/repositories/creating-and-managing-repositories/duplicating-a-repository).

Keep this directory: the installer uses it directly, rather than copying all runtime code elsewhere. Moving/deleting it breaks the installed paths; rerun the installer from the new location if you move it.

## 2. Edit the configuration in that directory

Open **`vaultin.yaml` in the root of the checkout you just cloned**, using your editor. Change these two values:

```yaml
repository: octocat/Vaultin-Personal
project_vault_owner: octocat
```

`repository` is the repository that holds your Vaultin configuration/knowledge, **not the application repository you want Codex to work on**. If you renamed your private copy, include that actual name. For evaluation without your own remote, use `CarlossgLuz/Open-Vaultin` as the repository identifier and keep publication disabled.

The complete example is:

```yaml
version: 1
repository: octocat/Vaultin-Personal
project_vault_owner: octocat
project_vault_prefix: vault-
fail_closed: true
runtime_dir_name: .vaultin-runtime
```

| Field | What to do | Meaning |
|---|---|---|
| `version` | Keep `1` | Configuration schema version. |
| `repository` | Set your actual `owner/repository` | Canonical Vaultin repository identifier. |
| `project_vault_owner` | Set your GitHub username | Owner validated when provisioning project-vault replicas. The current GitHub helper creates repositories for the authenticated user via `/user/repos`; organization provisioning is not implemented by this helper. |
| `project_vault_prefix` | Usually keep `vault-` | A project `example-api` has replica name `vault-example-api`. |
| `fail_closed` | Keep `true` | Governance intent; it does not prove the client provides full enforcement. |
| `runtime_dir_name` | Keep `.vaultin-runtime` | Local operational state directory inside this checkout. |

Unknown YAML fields are rejected. **Do not add `api_key`, `token` or `TYPESAFE_API_KEY` to this file.** For your private copy, commit the non-secret configuration:

```bash
git add vaultin.yaml
git commit -m "chore: configure personal Vaultin repository"
git push origin main
```

## 3. Configure the JEV API key (optional)

**Where does the token go?** Into the environment variable **`TYPESAFE_API_KEY` on the machine running Codex**. Vaultin reads it from the hook process environment. It does **not** automatically load `.env`, and there is no token field in `vaultin.yaml` or the Vaultin plugin settings.

1. Open the [TypeSafe console API keys page](https://console.typesafe.ai/keys), sign in, and obtain an API key using the console's current controls. Check service access and billing in your account.
2. Configure that key using the OS instructions below.
3. Restart/launch Codex from an environment that actually contains the variable.

Use a **TypeSafe API key**, not a GitHub token or a Codex/OpenAI credential. The current adapter calls `https://api.typesafe.ai/v1/systemone`, uses `jev-latest`, and supplies `Authorization: Bearer <key>` itself. Store the raw key without adding `Bearer `. No separate JEV daemon, router hook or SDK is required for this HTTP integration. See the [official API reference](https://api.typesafe.ai/redoc).

When enabled, the routing request sends the task text, working directory and current project identifier to TypeSafe. Use a non-sensitive prompt for validation.

### Windows PowerShell: current session and persistent user setting

Paste this into **PowerShell**. Enter your real key at the hidden prompt; this avoids putting the key in the command history:

```powershell
$JevSecret = Read-Host "TypeSafe API key" -AsSecureString
$env:TYPESAFE_API_KEY = [System.Net.NetworkCredential]::new("", $JevSecret).Password
[Environment]::SetEnvironmentVariable("TYPESAFE_API_KEY", $env:TYPESAFE_API_KEY, "User")
Remove-Variable JevSecret
```

This sets the current terminal variable and persists it for your Windows user. The persisted environment value is **not an encrypted secret vault**; do not use this method on a shared account.

Close Codex completely and reopen it. Existing processes do not receive the updated environment automatically. For the CLI, run `codex` from this same PowerShell terminal. For a desktop client, also restart any launcher/IDE that was already running; if it still inherits the old environment, sign out of Windows and back in.

Verify presence **without printing the key**:

```powershell
if ([string]::IsNullOrWhiteSpace($env:TYPESAFE_API_KEY)) {
    "TYPESAFE_API_KEY: missing in this terminal"
} else {
    "TYPESAFE_API_KEY: configured in this terminal"
}
```

### Linux Bash: current terminal

```bash
read -rsp 'TypeSafe API key: ' TYPESAFE_API_KEY
printf '\n'
export TYPESAFE_API_KEY
```

Run `codex` from this same terminal after installation. The key expires from this shell environment when you close it; setting it here does not update an already-running desktop client.

### Linux Bash: optional persistence

If you want to avoid entering the key for every new terminal, keep it in a restricted local file **outside the repository**:

```bash
mkdir -p "$HOME/.config/vaultin"
touch "$HOME/.config/vaultin/jev.env"
chmod 600 "$HOME/.config/vaultin/jev.env"
```

Open `~/.config/vaultin/jev.env` in your editor and add one line, replacing the example with your real key:

```bash
export TYPESAFE_API_KEY='PASTE_YOUR_REAL_TYPESAFE_KEY_HERE'
```

Load it before launching Codex:

```bash
source "$HOME/.config/vaultin/jev.env"
codex
```

For interactive Bash terminals, you may add `source "$HOME/.config/vaultin/jev.env"` to `~/.bashrc`. This is a plaintext file protected by filesystem permissions, not an encrypted secret store. A desktop launcher, systemd service, WSL instance or container does not automatically source your `.bashrc`; supply the variable through that environment's own launcher/secret configuration. Zsh users must adapt the shell startup file.

Verify presence without printing the key:

```bash
if [ -n "${TYPESAFE_API_KEY:-}" ]; then
  printf 'TYPESAFE_API_KEY: configured in this terminal\n'
else
  printf 'TYPESAFE_API_KEY: missing in this terminal\n'
fi
```

**Skipping JEV is supported.** Without a key, Vaultin uses deterministic fallback. A configured variable proves only that a key is present, not that it is valid or that JEV accepted a request.

## 4. Run the installer from the Vaultin checkout

Windows PowerShell:

```powershell
.\scripts\install.ps1
```

Linux Bash:

```bash
bash scripts/install.sh
```

If Windows blocks script execution, review the script and your machine's policy before changing it; follow organization policy on managed machines. On Linux, Python must include venv/pip support. Installation requires access to the configured Python package index.

The installer creates `~/.vaultin/venv`, installs this checkout in editable mode, stores its absolute path in `~/.vaultin/root`, creates CLI/hook wrappers and registers the Codex plugin and hooks. On Windows, `~` means your user profile directory.

| User file/directory | What the installer writes |
|---|---|
| `~/.vaultin/root` | Path to the canonical Vaultin checkout. |
| `~/.vaultin/bin/` | CLI and lifecycle hook wrappers. |
| `~/.agents/plugins/marketplace.json` | Local plugin marketplace entry. |
| `~/.codex/config.toml` | Enabled Vaultin plugin entry. |
| `~/.codex/hooks.json` | User lifecycle hooks; unrelated groups are preserved. |
| `~/.codex/plugins/vaultin/` | Local plugin assets. |

It replaces the installed Vaultin plugin directory/cache and finishes with the core health gate. It does **not** save your TypeSafe key, install Codex, authenticate GitHub, or configure every other AI client.

The current Windows hook helper rejects a wrapper path containing whitespace (for example a Windows user-profile path with spaces). Treat that installer error as an unsupported path, rather than assuming installation succeeded.

## 5. Check the installed runtime

While still in the **Vaultin checkout**, run:

```text
vaultinctl health
vaultinctl doctor
vaultinctl status
```

If `vaultinctl` is not found, use the actual installed wrapper:

Windows PowerShell:

```powershell
& "$HOME\.vaultin\bin\vaultinctl.cmd" health --root (Get-Location).Path
& "$HOME\.vaultin\bin\vaultinctl.cmd" doctor --root (Get-Location).Path
& "$HOME\.vaultin\bin\vaultinctl.cmd" status --root (Get-Location).Path
```

Linux Bash:

```bash
"$HOME/.vaultin/bin/vaultinctl" health --root "$PWD"
"$HOME/.vaultin/bin/vaultinctl" doctor --root "$PWD"
"$HOME/.vaultin/bin/vaultinctl" status --root "$PWD"
```

On Windows the installer adds its wrapper directory to the user/current PATH. On Linux it links the CLI under `~/.local/bin`; that directory must be on your shell's PATH to use the short command.

| Command | Actual current behavior |
|---|---|
| `health` | Checks configuration, active source checkout, policy, workflow, agents, skills and ledger. Expected overall result: `PASS`. |
| `doctor` | Prints runtime source/root and runs the same core health checks. |
| `status` | Runs core health checks and prints `pending_sync`. |

These commands **do not test the TypeSafe API key, GitHub authentication, or whether your live Codex client executes hooks**. Their default `--root` is the current working directory. From an application project, explicitly pass the absolute **Vaultin checkout** path; do not pass the application path as the governance root.

## 6. Start a real Codex session in your application project

1. Completely restart Codex after installation.
2. Check that the installed Vaultin plugin is enabled and review/trust the local hooks if the client asks.
3. Open the application repository you actually want to work on. Keep the Vaultin checkout in its original location.
4. For Codex CLI, change to that application's directory and launch `codex` from the terminal where you configured `TYPESAFE_API_KEY`.
5. Send a harmless task, for example: **“Explain this repository's structure without editing files.”**

The installed hook wrapper pins the Vaultin checkout with `--root`; the active application's working directory identifies the project. You do not need to copy `vaultin.yaml`, the token or the hooks into each application repository.

Compatible clients can run the installed events `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, `Interrupt` and `SessionEnd`. Vaultin records routing and execution state locally. Hook enforcement still depends on what the host actually implements; installing Vaultin on your PC does not attach it to an unrelated remote/browser session.

## 7. Verify that JEV actually routed the task

After the test prompt, return to the **Vaultin checkout** in another terminal. Use the installed Python to inspect the latest recorded routing event. This reads the ledger without printing the key or the task text.

Windows PowerShell:

```powershell
@'
import json, sqlite3
from pathlib import Path
from vaultin.paths import VaultinPaths
path = VaultinPaths.from_root(Path.cwd()).ledger_db
with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
    row = db.execute("SELECT execution_id, payload_json FROM events WHERE kind = 'ROUTED' ORDER BY created_at DESC, sequence DESC LIMIT 1").fetchone()
if row is None:
    print("No routing event yet: check live-client hook execution.")
else:
    route = json.loads(row[1])
    print("execution_id:", row[0])
    print("source:", route.get("source"))
    print("fallback_reason:", route.get("fallback_reason"))
'@ | & "$HOME\.vaultin\venv\Scripts\python.exe" -
```

Linux Bash:

```bash
"$HOME/.vaultin/venv/bin/python" - <<'PYTHON'
import json, sqlite3
from pathlib import Path
from vaultin.paths import VaultinPaths
path = VaultinPaths.from_root(Path.cwd()).ledger_db
with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
    row = db.execute("SELECT execution_id, payload_json FROM events WHERE kind = 'ROUTED' ORDER BY created_at DESC, sequence DESC LIMIT 1").fetchone()
if row is None:
    print("No routing event yet: check live-client hook execution.")
else:
    route = json.loads(row[1])
    print("execution_id:", row[0])
    print("source:", route.get("source"))
    print("fallback_reason:", route.get("fallback_reason"))
PYTHON
```

| Result | Meaning / next action |
|---|---|
| `source: jev` | JEV returned a route accepted by Vaultin for this execution. |
| `source: fallback` | Deterministic routing was used. Read `fallback_reason`; this does not by itself indicate failed governance. |
| `source: explicit` | A supported `workflow=...` directive chose the workflow before JEV. Omit the directive when testing JEV. |
| `jev_http_error` | HTTP/network/timeout failure; the current classifier does not expose the HTTP status. Check your TypeSafe account/key, connectivity and timeout. |
| `jev_schema_error` | Response did not satisfy the adapter's expected contract. |
| `low_agent_confidence` / `low_workflow_confidence` | JEV answered, but the required decision confidence was too low. |
| No event / missing ledger | The prompt may not have reached the hooks, may have failed before routing, or you are inspecting the wrong checkout. Check the client's hook output and `~/.vaultin/hook-errors.log` if present. |

The last event can belong to another concurrent session; use its `execution_id` to match the tested turn. A `health: PASS` result alone is not proof of JEV integration.

## 8. Understand GitHub synchronization and secondary clients

JEV routing needs only `TYPESAFE_API_KEY`. Normal Git push/pull needs your Git credentials. The optional project-replica provisioning helper separately reads **`GITHUB_TOKEN`** and creates private repositories for the authenticated personal account; its token must have the permissions required for that operation. Logging into Git does not automatically set `GITHUB_TOKEN`, and the YAML does not create repositories by itself.

Do not enable publication just to test installation. Receipts remain local by default (`VAULTIN_PUBLISH_RECEIPTS` unset); MCP publication is also disabled (`VAULTIN_MCP_ALLOW_PUBLISH` unset). Review knowledge and metadata before publishing anything, even to a private remote.

Other clients require their own integration. For a client supporting **stdio MCP**, configure its server command as the absolute installed executable:

- Windows: `C:\Users\YOUR_USER\.vaultin\venv\Scripts\vaultin-mcp.exe`
- Linux: `/home/YOUR_USER/.vaultin/venv/bin/vaultin-mcp`

No server arguments are needed for the default root recorded by the installer. The host starts the process; exact settings location/JSON format depend on that client. An MCP connection provides Vaultin knowledge tools, **not automatic Codex lifecycle hooks or JEV routing for that client's every prompt**. See [Client integrations](docs/client-integrations.md).

## 9. Update or disable the integration

For your private copy, fetch reviewed upstream updates, merge them and rerun the installer when dependencies, wrappers or hook definitions change. Resolve any conflicts in your own configuration before continuing:

```bash
git fetch upstream
git merge upstream/main
```

Restart Codex and repeat the health and live-session checks after a material update.

To disable JEV, remove `TYPESAFE_API_KEY` from the current environment and its persistence location, then restart the client. On Windows:

```powershell
Remove-Item Env:TYPESAFE_API_KEY -ErrorAction SilentlyContinue
[Environment]::SetEnvironmentVariable("TYPESAFE_API_KEY", $null, "User")
```

On Linux run `unset TYPESAFE_API_KEY` and remove the export/source from your local secret/startup file. This leaves deterministic routing available. Revoke the key in TypeSafe if you want to invalidate the credential itself.

There is currently no automatic uninstaller. To disable Vaultin entirely, remove only its hook groups (commands containing `vaultinctl-hook`) from `~/.codex/hooks.json`, disable the Vaultin plugin entry in `~/.codex/config.toml`, and restart Codex. Preserve other plugins/hooks and back up user configuration before manual edits. Disabling only the plugin can leave the separately installed user hooks active.

---

# JEV and token economy

When configured, JEV performs typed routing before Codex receives execution context.

Instead of sending the full classifier exchange to the model, Vaultin passes a compact validated result such as:

- workflow;
- agent;
- skills;
- execution id.

`VAULTIN_JEV_TIMEOUT_SECONDS` defaults to **3 seconds** and is constrained to the safe range of **0.5–5 seconds**.

If JEV is unavailable, invalid or insufficiently confident, Vaultin falls back deterministically.

JEV does **not** replace policy enforcement.

---

# MCP

Vaultin also exposes a narrow MCP interface for secondary AI clients.

Use the absolute executable under `~/.vaultin/venv/bin/` (Linux) or `~/.vaultin/venv/Scripts/` (Windows), as shown in step 8. The installer does not add this venv directory to PATH.

The MCP interface is intentionally restricted. It exposes canonical knowledge and project-vault operations without turning Vaultin into a generic filesystem server.

Git publication through MCP is disabled by default and requires explicit opt-in.

---

# Important environment variables

| Variable | Required? | Purpose |
|---|---|---|
| `VAULTIN_ROOT` | No | Overrides the canonical Vaultin repository path. |
| `TYPESAFE_API_KEY` | No | Raw TypeSafe key inherited by the client/hooks; see step 3. |
| `GITHUB_TOKEN` | Only for replica provisioning | GitHub API authentication for the optional private-repository helper; separate from Git credentials. |
| `VAULTIN_MCP_ALLOW_PUBLISH` | No | Enables Git publication from MCP when explicitly opted in. |
| `VAULTIN_PUBLISH_RECEIPTS` | No | Enables publication of execution receipts. Disabled by default. |
| `VAULTIN_JEV_TIMEOUT_SECONDS` | No | Controls the JEV request timeout within the allowed range. |
| `PYTHON` | No | Overrides the Python interpreter used by the installer. |

For the complete reference, see [Configuration](docs/configuration.md).

---

# Privacy defaults

Open-Vaultin ships with conservative defaults:

- `memory/` is ignored by Git;
- `.vaultin-runtime/` is ignored by Git;
- execution receipt publication is disabled by default;
- MCP Git publication is disabled by default;
- public fixtures use generic example repositories;
- no personal Vaultin memory is included in this repository.

Runtime state should not be treated as durable user-facing knowledge.

---

# Repository structure

```text
.agents/skills/        Agent Skills catalog
agents/                Agent profiles and registry
policies/              Governance policy
workflows/             Execution state machine
src/vaultin/           Core runtime
adapters/              Client integration assets
scripts/               Windows/Linux installers
vaults/                Canonical project-vault registry
knowledge/             Global durable knowledge surface
docs/                  Technical and operational documentation
tests/                 Unit and integration tests
evals/                 Behavioral evaluation cases
.github/                CI and community automation
```

---

# Troubleshooting

If something does not work after installation, start with:

```text
vaultinctl health
vaultinctl doctor
vaultinctl status
```

Then check:

1. Python is version 3.11 or newer;
2. Git is available in the terminal;
3. `vaultin.yaml` contains the correct GitHub owner/repository;
4. the Vaultin repository still exists at the path referenced by `~/.vaultin/root`;
5. the AI client was restarted after installation;
6. lifecycle hooks were trusted when requested;
7. required environment variables are available in the process that launches the AI client.

For more cases, see [Troubleshooting](docs/troubleshooting.md).

---

# Documentation

If you are new to Vaultin, read these in this order:

1. [Getting started](docs/getting-started.md)
2. [Configuration](docs/configuration.md)
3. [Client integrations](docs/client-integrations.md)
4. [Architecture](docs/architecture.md)
5. [Troubleshooting](docs/troubleshooting.md)

Additional references:

- [Installation](docs/operations/install.md)
- [Recovery](docs/operations/recovery.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Roadmap](ROADMAP.md)
- [Release process](docs/releasing.md)

---

# Development

Install development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

The official CI validates Windows and Linux.

---

# Security

Do not publish suspected vulnerabilities that could expose:

- credentials;
- private project knowledge;
- unsafe hook behavior;
- synchronization bypasses;
- sensitive execution state.

See [SECURITY.md](SECURITY.md).

---

# Contributing

Bug reports, fixes and focused improvements are welcome.

Before submitting changes:

1. read [CONTRIBUTING.md](CONTRIBUTING.md);
2. remove personal/private environment data from logs and examples;
3. run the test suite;
4. make sure documentation matches the actual runtime behavior;
5. update both English and PT-BR README versions when changing setup instructions.

---

# License

Open-Vaultin is distributed under the **MIT License**.

See [LICENSE](LICENSE).
