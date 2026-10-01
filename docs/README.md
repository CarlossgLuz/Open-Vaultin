# Vaultin documentation

This directory contains the operational and technical documentation for Vaultin.

If you are new to the project, read the documents in this order:

1. [Getting started](getting-started.md) — install, verify, and run Vaultin for the first time.
2. [Architecture](architecture.md) — understand the control flow, trust boundaries, lifecycle, routing, policy, ledger, and vault synchronization.
3. [Configuration](configuration.md) — repository configuration, environment variables, policies, agents, skills, and runtime paths.
4. [Client integrations](client-integrations.md) — Codex lifecycle hooks and the MCP surface for secondary AI clients.
5. [Troubleshooting](troubleshooting.md) — health failures, hook issues, sync states, replica divergence, JEV fallback, and recovery.
6. [Release process](releasing.md) — release gate, semantic versioning, and manual publication workflow.

## Operations

The `operations/` directory contains runbooks for day-to-day and cutover-sensitive procedures:

- [Installation](operations/install.md)
- [Recovery](operations/recovery.md)
- [Multi-AI operation](operations/multi-ai.md)
- [Cutover](operations/cutover.md)

## Source of truth

For current behavior, prefer the README, this documentation set, source code, tests, and the release-readiness runbook. Environment-specific acceptance evidence is intentionally not shipped in the public template.
