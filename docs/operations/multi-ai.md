# Multi-AI operation

Vaultin is Codex-first while keeping one canonical knowledge/governance repository for other AI clients.

## Codex

Codex receives the deepest integration through the Vaultin plugin and lifecycle hooks. Vaultin still reports actual capability level: hooks are not described as a complete enforcement boundary when the active Codex surface does not provide one.

## Claude, Gemini, and Copilot

Secondary adapters expose the detected capability level as `partial` or `context-only`. They can use the same canonical Vaultin knowledge through the local MCP surface.

The MCP server is narrow by design: search canonical knowledge, read allowed canonical artifacts, write Markdown into a canonical project vault, inspect the vault registry, and create receipts. It is not a generic filesystem server.

When `VAULTIN_MCP_ALLOW_PUBLISH=1` is explicitly configured, a canonical project-vault write may request `publish=true`; Vaultin then commits and pushes only the canonical Vaultin path through its Git wrapper. Replica repositories remain projection targets, not editing targets.

Live host validation for Claude, Gemini, and Copilot remains a cutover criterion and is recorded independently from the automated contract tests.
