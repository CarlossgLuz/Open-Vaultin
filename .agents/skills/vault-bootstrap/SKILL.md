---
name: vault-bootstrap
description: Bootstrap a governed Vaultin session by validating health, discovering the project, loading policy/agents/skills, resolving the canonical project vault, starting the ledger, and routing through JEV or deterministic fallback.
version: 1.0.0
source: vaultin-core
---

# Vault bootstrap

1. Require `vaultinctl health` to pass for critical local controls.
2. Discover the current project from Git metadata; do not inject Vaultin control files into the source repository.
3. Ensure a persistent project has its canonical Vaultin vault and private personal replica.
4. Load policy, workflow state machine, core agent registry, and canonical Agent Skills.
5. Begin the execution ledger and record the client/cwd.
6. Route with JEV when available; use deterministic fallback on classifier failure/low confidence.
7. Stop rather than silently weaken governance when a required critical control is unavailable.

No manual daemon start is required for the governance bootstrap.
