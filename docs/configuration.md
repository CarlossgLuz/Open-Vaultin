# Configuration reference

Vaultin configuration is intentionally small. Most behavior is derived from canonical registries and policies rather than one large mutable settings file.

## Repository configuration: `vaultin.yaml`

Current V1 schema:

```yaml
version: 1
repository: YOUR_GITHUB_USER/Open-Vaultin
project_vault_owner: YOUR_GITHUB_USER
project_vault_prefix: vault-
fail_closed: true
runtime_dir_name: .vaultin-runtime
```

The settings model rejects unknown fields.

### Fields

#### `version`

Configuration schema version.

Current value:

```yaml
version: 1
```

#### `repository`

Canonical Vaultin repository identifier.

```yaml
repository: YOUR_GITHUB_USER/Open-Vaultin
```

#### `project_vault_owner`

Configured owner value for the project-vault model.

```yaml
project_vault_owner: YOUR_GITHUB_USER
```

`VaultRegistry` uses this value when validating newly created private replicas.

#### `project_vault_prefix`

Configured prefix for replica repository names.

```yaml
project_vault_prefix: vault-
```

A project slug `example-api` maps to:

```text
vault-example-api
```

Replica provisioning and pending-sync reconciliation use this configured prefix.

#### `fail_closed`

Declares fail-closed intent for governance.

```yaml
fail_closed: true
```

Actual client enforcement capability is still probed separately. Vaultin does not infer a complete enforcement boundary from this setting alone.

#### `runtime_dir_name`

Name of the local runtime directory.

```yaml
runtime_dir_name: .vaultin-runtime
```

The runtime path helper resolves the ledger, event stream, synchronization queue, indexes, and session state under the configured directory name.

## User-level Vaultin state

The installer creates:

Linux/macOS-style path:

```text
~/.vaultin/
```

Windows:

```text
%USERPROFILE%\.vaultin\
```

Typical contents:

```text
.vaultin/
├── root
├── venv/
├── bin/
└── hook-errors.log   # created when hook failures are recorded
```

The `root` file stores the canonical Vaultin checkout used by hooks and the MCP server.

## Environment variables

### `VAULTIN_ROOT`

Optional absolute/expandable path to the canonical Vaultin checkout.

Resolution priority for hooks is:

1. explicit CLI `--root`;
2. `VAULTIN_ROOT`;
3. `~/.vaultin/root`.

Example:

```bash
export VAULTIN_ROOT="$HOME/src/Open-Vaultin"
```

### `TYPESAFE_API_KEY`

Optional API key used by `HttpJevClassifier`.

When absent or invalid, JEV routing fails into the deterministic fallback path.

Example:

```bash
export TYPESAFE_API_KEY="..."
```

Do not commit this value.

### `VAULTIN_MCP_ALLOW_PUBLISH`

Optional opt-in for Git publication from the MCP server.

Truthy values accepted by the current runtime include:

```text
1
true
yes
```

When disabled, MCP project-vault writes remain local canonical writes unless publication is performed through another governed path.

### `VAULTIN_PUBLISH_RECEIPTS`

Optional opt-in for publishing local execution receipts through Git. It is disabled by default because receipts can contain project paths, task objectives, Git evidence, and other environment-specific context.

Truthy values include `1`, `true`, `yes`, and `on`.

### `VAULTIN_JEV_TIMEOUT_SECONDS`

Optional timeout budget for JEV routing inside `UserPromptSubmit`. The runtime clamps the value to the safe range of 0.5–5 seconds and defaults to 3 seconds, preventing a slow classifier request from consuming the whole hook budget.

### `PYTHON`

Optional installer override.

Linux:

```bash
PYTHON=python3.12 bash scripts/install.sh
```

PowerShell:

```powershell
$env:PYTHON = "py"
.\scripts\install.ps1
```

The selected interpreter must resolve to Python 3.11+.

## Policy configuration

Canonical policy:

```text
policies/core.yaml
```

Current V1:

```yaml
critical:
  deny_actions:
    - disable_governance
project: {}
```

Policy evaluation order is:

1. critical policy;
2. project policy;
3. project-native instructions;
4. explicit user authorization;
5. agent defaults.

Critical and project denials are evaluated before lower-level allow sources.

Do not use the router as a substitute for policy.

## Agent registry

Canonical registry:

```text
agents/registry.yaml
```

Each entry maps a stable agent name to a profile file.

Example:

```yaml
- name: software-engineer
  profile: agents/profiles/software-engineer.yaml
```

Routing output is validated against this registry.

When adding an agent:

1. add its profile under `agents/profiles/`;
2. register it in `agents/registry.yaml`;
3. update tests/acceptance evidence where applicable;
4. run the full test suite;
5. verify that routing and downstream workflows understand the new agent.

## Skill catalog

Canonical catalog:

```text
.agents/skills/catalog.json
```

Each skill entry contains:

- stable `name`;
- canonical `path`;
- semantic `version`.

Routing cannot select an unknown skill.

## Project-vault registry

Canonical registry:

```text
vaults/registry.yaml
```

Initial state:

```yaml
version: 1
projects: {}
```

Provisioned entries contain:

- source repository when known;
- canonical project-vault path;
- replica repository;
- synchronization mode.

The registry is file-locked during mutation.

Avoid editing a replica repository as if it were canonical. Reconcile changes in Vaultin first.

## Codex configuration written by the installer

The installer manages several user-level files:

```text
~/.agents/plugins/marketplace.json
~/.codex/config.toml
~/.codex/hooks.json
~/.codex/plugins/vaultin/
```

The install helper:

- preserves unrelated marketplace entries;
- preserves unrelated lifecycle hooks;
- replaces stale Vaultin hook groups;
- validates TOML/JSON before replacing user configuration;
- backs up malformed hook JSON before rebuilding a valid structure.

## Runtime data

Operational state lives under:

```text
.vaultin-runtime/
```

Key files:

```text
vaultin.db
events.jsonl
sync-queue.jsonl
replica-state.json
search.db
```

Not every file is guaranteed to exist before the corresponding subsystem is used.

Treat runtime files as implementation state. Durable human-facing knowledge belongs under the canonical knowledge/memory paths instead.

## Secrets

Do not write API keys, access tokens, passwords, or other secrets into:

- `vaultin.yaml`;
- project vault notes;
- agent profiles;
- skill files;
- durable execution receipts.

Use environment variables or an external secret manager appropriate to the host environment.

Vaultin's repository guidance explicitly requires an explicit project policy before any secret value could be considered durable data.
