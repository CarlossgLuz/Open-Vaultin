# Open-Vaultin

[![CI](https://github.com/CarlossgLuz/Open-Vaultin/actions/workflows/ci.yml/badge.svg)](https://github.com/CarlossgLuz/Open-Vaultin/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Early V1](https://img.shields.io/badge/status-early%20V1-orange.svg)](CHANGELOG.md)

**Open-Vaultin** is the open-source distribution of Vaultin: a local-first governance and durable-knowledge layer for AI-assisted software engineering.

It provides a shared, auditable control plane for **agents, skills, policies, routing, execution lifecycle, project knowledge, evidence and Git-backed synchronization** without requiring Vaultin-specific files inside every source repository.

> **Status:** early V1 / pre-1.0. The core runtime is implemented and validated on Windows and Linux, but real client integrations must still be validated in the environment where Vaultin is installed.

## What problem does it solve?

AI coding environments easily accumulate fragmented state:

- each AI client sees a different context;
- knowledge is lost between sessions;
- agents and skills drift over time;
- interrupted executions can leave stale state behind;
- model routing gets confused with authorization;
- generated changes are difficult to audit;
- synchronization failures can silently disappear.

Open-Vaultin separates those concerns and gives them one canonical home.

## Core model

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

## Recommended usage

For real personal use, **fork this repository into a private repository**.

Your private fork can safely accumulate your own:

- project vaults;
- knowledge;
- operational configuration;
- execution history;
- local integrations.

Do **not** publish personal memory, credentials, prompts, private repository names, filesystem paths or proprietary project knowledge.

## Requirements

- Python **3.11+**
- Git
- Windows or Linux
- optional `TYPESAFE_API_KEY` for JEV routing
- a compatible Codex/ChatGPT surface for lifecycle hooks

## Quick start

### 1. Fork or clone

For evaluation:

```bash
git clone https://github.com/CarlossgLuz/Open-Vaultin.git
cd Open-Vaultin
```

For daily personal use, prefer a **private fork**.

### 2. Configure

Edit `vaultin.yaml`:

```yaml
version: 1
repository: YOUR_GITHUB_USER/Open-Vaultin
project_vault_owner: YOUR_GITHUB_USER
project_vault_prefix: vault-
fail_closed: true
runtime_dir_name: .vaultin-runtime
```

### 3. Install

Windows:

```powershell
.\scripts\install.ps1
```

Linux:

```bash
bash scripts/install.sh
```

The installer creates an isolated environment under `~/.vaultin` / `%USERPROFILE%\.vaultin`, installs Vaultin in **editable mode**, registers the local Codex integration and runs the health gate.

### 4. Verify

```text
vaultinctl health
vaultinctl doctor
vaultinctl status
```

After the first installation or a material hook change, restart the client and perform the one-time local-hook trust review when prompted.

## Lifecycle

```text
SessionStart
→ UserPromptSubmit
→ JEV / deterministic routing
→ PreToolUse / PostToolUse
→ Stop or Interrupt
→ evidence + receipt
→ SessionEnd
```

A stale or interrupted execution is recovered so it does not permanently block the next prompt.

## JEV and token economy

When configured, JEV performs typed routing before Codex receives execution context.

The model receives only the compact validated route — such as workflow, agent, skills and execution id — rather than the entire classifier exchange.

`VAULTIN_JEV_TIMEOUT_SECONDS` defaults to 3 seconds and is bounded to 0.5–5 seconds.

If JEV is unavailable, invalid or insufficiently confident, Vaultin falls back deterministically without expanding policy authority.

## MCP

Start the MCP server with:

```text
vaultin-mcp
```

The MCP interface is deliberately narrow. It can expose canonical knowledge operations and project-vault writes without becoming a generic filesystem server.

Git publication through MCP is disabled by default and requires explicit opt-in.

## Privacy defaults

Open-Vaultin ships with conservative defaults:

- `memory/` is ignored by Git;
- `.vaultin-runtime/` is ignored by Git;
- execution receipt publication is disabled by default;
- MCP Git publication is disabled by default;
- public fixtures use generic example repositories;
- no personal Vaultin memory is included in this repository.

## Repository layout

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

## Documentation

Start with:

- [Getting started](docs/getting-started.md)
- [Architecture](docs/architecture.md)
- [Configuration](docs/configuration.md)
- [Client integrations](docs/client-integrations.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Installation](docs/operations/install.md)
- [Recovery](docs/operations/recovery.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```

The official CI validates Windows and Linux.

## Security

Do not publish suspected vulnerabilities that could expose credentials, private knowledge, unsafe hook behavior or synchronization bypasses.

See [SECURITY.md](SECURITY.md).

## Contributing

Bug reports, fixes and focused improvements are welcome.

Please read [CONTRIBUTING.md](CONTRIBUTING.md) and remove personal/private environment data from logs and examples before submitting anything.

## License

Open-Vaultin is currently distributed under the **MIT License**.

See [LICENSE](LICENSE).
