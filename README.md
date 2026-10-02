# Open-Vaultin

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

For regular personal use, the recommended setup is to **fork Open-Vaultin into a private repository**.

Your private fork can safely accumulate your own:

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

# Quick start

## 1. Fork or clone the repository

### Option A — Testing only

If you only want to evaluate Vaultin:

```bash
git clone https://github.com/CarlossgLuz/Open-Vaultin.git
cd Open-Vaultin
```

### Option B — Recommended for personal use

Create a **private fork** of Open-Vaultin in your GitHub account, then clone your fork:

```bash
git clone https://github.com/YOUR_GITHUB_USER/Open-Vaultin.git
cd Open-Vaultin
```

Replace `YOUR_GITHUB_USER` with your real GitHub username or organization.

Example:

```text
YOUR_GITHUB_USER = octocat
```

Then:

```text
https://github.com/octocat/Open-Vaultin.git
```

---

## 2. Configure `vaultin.yaml`

This is the part most users need to change before installation.

Open:

```text
vaultin.yaml
```

The default file looks like this:

```yaml
version: 1
repository: YOUR_GITHUB_USER/Open-Vaultin
project_vault_owner: YOUR_GITHUB_USER
project_vault_prefix: vault-
fail_closed: true
runtime_dir_name: .vaultin-runtime
```

### What do I actually need to edit?

For a standard installation, **you normally only need to replace `YOUR_GITHUB_USER` in two places**.

For example, if your GitHub username is:

```text
octocat
```

Change this:

```yaml
repository: YOUR_GITHUB_USER/Open-Vaultin
project_vault_owner: YOUR_GITHUB_USER
```

To this:

```yaml
repository: octocat/Open-Vaultin
project_vault_owner: octocat
```

Your final configuration would look like:

```yaml
version: 1
repository: octocat/Open-Vaultin
project_vault_owner: octocat
project_vault_prefix: vault-
fail_closed: true
runtime_dir_name: .vaultin-runtime
```

### Configuration fields

| Field | Change it? | Meaning |
|---|---|---|
| `version` | No | Vaultin configuration schema version. Keep `1` for the current V1 format. |
| `repository` | **Yes** | GitHub repository used as the canonical Vaultin repository. |
| `project_vault_owner` | **Yes** | GitHub user or organization that will own project-vault repositories. |
| `project_vault_prefix` | Usually no | Prefix used for project-vault repository names. Default: `vault-`. |
| `fail_closed` | Usually no | Declares fail-closed governance intent. Keep `true` unless you explicitly understand the consequences of changing it. |
| `runtime_dir_name` | Usually no | Name of the local runtime-state directory. Default: `.vaultin-runtime`. |

### Example: project vault naming

With:

```yaml
project_vault_prefix: vault-
```

A project called:

```text
example-api
```

maps to a project-vault name such as:

```text
vault-example-api
```

### Important: secrets do not belong in `vaultin.yaml`

Do not place API keys, tokens, passwords or other credentials in this file.

For example, `TYPESAFE_API_KEY` must be configured as an **environment variable**, not written into YAML.

---

## 3. Optional — configure JEV / TypeSafe

JEV routing is optional.

If you do not configure it, Vaultin uses its deterministic fallback path.

### Windows PowerShell

For the current terminal session:

```powershell
$env:TYPESAFE_API_KEY = "your-key"
```

### Linux

```bash
export TYPESAFE_API_KEY="your-key"
```

Do not commit API keys to Git.

---

## 4. Install Vaultin

### Windows

From the repository root:

```powershell
.\scripts\install.ps1
```

### Linux

```bash
bash scripts/install.sh
```

The installer:

1. creates an isolated environment under `~/.vaultin` or `%USERPROFILE%\.vaultin`;
2. installs Vaultin in editable mode;
3. registers the local Codex integration;
4. configures Vaultin lifecycle hooks;
5. runs the installation health gate.

The canonical Vaultin repository path is stored under:

### Windows

```text
%USERPROFILE%\.vaultin\root
```

### Linux

```text
~/.vaultin/root
```

---

## 5. Verify the installation

Run:

```text
vaultinctl health
vaultinctl doctor
vaultinctl status
```

### What should these commands tell me?

- `vaultinctl health` checks whether the core Vaultin installation is healthy.
- `vaultinctl doctor` performs broader diagnostics for configuration and integrations.
- `vaultinctl status` shows the current Vaultin/runtime state.

If the commands are unavailable immediately after installation, open a new terminal and try again.

After the first installation or a material lifecycle-hook change, restart the AI client.

If the client asks you to review or trust local hooks, perform that one-time review before continuing.

---

## 6. Start using Vaultin

Once installed, normal AI-client execution goes through the Vaultin lifecycle:

```text
SessionStart
→ UserPromptSubmit
→ JEV / deterministic routing
→ PreToolUse / PostToolUse
→ Stop or Interrupt
→ evidence + receipt
→ SessionEnd
```

Vaultin tracks execution state and can recover stale or interrupted executions so they do not permanently block later prompts.

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

Start it with:

```text
vaultin-mcp
```

The MCP interface is intentionally restricted. It exposes canonical knowledge and project-vault operations without turning Vaultin into a generic filesystem server.

Git publication through MCP is disabled by default and requires explicit opt-in.

---

# Important environment variables

| Variable | Required? | Purpose |
|---|---|---|
| `VAULTIN_ROOT` | No | Overrides the canonical Vaultin repository path. |
| `TYPESAFE_API_KEY` | No | Enables JEV / TypeSafe HTTP routing. |
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
4. make sure documentation matches the actual runtime behavior.

---

# License

Open-Vaultin is distributed under the **MIT License**.

See [LICENSE](LICENSE).
