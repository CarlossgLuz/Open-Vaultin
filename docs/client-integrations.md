# Client integrations

Vaultin is Codex-first, but its canonical knowledge/governance repository is designed to be consumed by more than one AI client.

The important rule is that every adapter must report the capability level it actually has. Vaultin does not promote a context-only integration to a full enforcement boundary.

## Codex

Codex receives the deepest V1 integration through a local plugin and lifecycle hooks.

### Installed hook events

```text
SessionStart
UserPromptSubmit
PreToolUse
PostToolUse
Stop
Interrupt
SessionEnd
```

The hook template lives at:

```text
adapters/codex-plugin/hooks/hooks.json
```

The installer copies the plugin into the user's Codex plugin directory and renders hook commands to an absolute Vaultin wrapper.

### Lifecycle responsibilities

#### SessionStart

Bootstraps the session-side Vaultin context.

#### UserPromptSubmit

Creates or restores the durable execution context and routes the current task.

#### PreToolUse

Provides the point where tool actions can be evaluated against active governance.

#### PostToolUse

Records post-action execution/validation context.

#### Stop

Finalizes the execution when possible, calculates changed paths/Git evidence, writes the durable receipt, and records the final state.

#### Interrupt

Releases an interrupted turn and marks any active execution as failed/recovered so the next prompt is not blocked by stale state.

#### SessionEnd

Cleans up session state and marks an unfinished execution as failed instead of letting it disappear silently.

### One-time trust

Local hooks are subject to the client's trust model.

After first installation or a material hook change, restart the client and approve the Vaultin hook when prompted.

Vaultin does not automatically bypass this security step.

### Capability reporting

The filesystem Codex probe detects whether lifecycle hooks are present, but it deliberately reports:

```text
complete_enforcement_boundary = false
```

unless a stronger surface can prove otherwise.

This prevents documentation or runtime code from claiming that local hooks provide guarantees the host does not technically expose.

## Secondary clients

Vaultin includes adapters for secondary AI clients such as Claude, Gemini, and Copilot.

V1 treats these integrations conservatively.

Depending on the host, their capability can be reported as:

- `partial`;
- `context-only`.

The shared integration surface is the Vaultin MCP server.

## MCP server

Start the server with:

```text
vaultin-mcp
```

It resolves Vaultin from `VAULTIN_ROOT` or `~/.vaultin/root`.

### Exposed tools

The current server exposes:

#### `search_knowledge`

Searches the canonical local knowledge index.

Inputs include:

- query;
- optional current project;
- result limit.

#### `read_canonical`

Reads a file only from allowed canonical surfaces.

Allowed top-level areas include:

```text
knowledge
memory
vaults
agents
.agents
policies
workflows
```

Absolute paths, empty paths, and traversal through `..` are rejected.

#### `write_project_note`

Writes Markdown only under an **existing** canonical project vault:

```text
vaults/projects/<project>/
```

The target file must have a `.md` suffix.

This is not a general file-write API.

#### `inspect_registry`

Returns the canonical project-vault registry.

### Git publication

MCP publication is disabled by default.

Enable it explicitly with:

```bash
export VAULTIN_MCP_ALLOW_PUBLISH=1
```

When enabled, `write_project_note(..., publish=true)` may commit and push the canonical Vaultin path using the Git wrapper.

This still does not make a replica repository canonical.

### Receipt publication

Codex execution receipts are local by default. Set `VAULTIN_PUBLISH_RECEIPTS=1` only when Git publication of receipt files is intentional and the content has been reviewed for environment-specific data.

## JEV and client integrations

JEV is used by the routing layer, not by the client adapter as an authorization system.

A secondary client can consume Vaultin knowledge even if JEV is unavailable.

The route source is recorded as either:

```text
jev
fallback
```

and fallback reasons are captured in the typed route proposal.

## Choosing the right integration mode

Use lifecycle hooks when the client supports them and when their semantics are understood.

Use MCP when the host needs controlled access to canonical knowledge but does not expose equivalent lifecycle control.

Do not assume feature parity between clients.

Live-client validation is environment-specific. Use the release-readiness runbook and validate each client in the environment where Vaultin is installed.
