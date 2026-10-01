---
name: typed-agent-handoff
description: Structure delegation between registered Vaultin agents with explicit objective, scope, allowed tools, evidence, stop conditions, and expected output without expanding authority.
version: 1.0.0
source: vaultin-core
---

# Typed agent handoff

1. Confirm the target agent exists in `agents/registry.yaml`.
2. Define objective, allowed/prohibited paths, relevant evidence, tools, validation, and stop conditions.
3. Keep inherited policy and user authorization unchanged; a delegated agent cannot broaden either.
4. Record the handoff in the current execution ledger.
5. If the host cannot create a true independent subagent, mark the handoff as emulated instead of claiming independent review.
6. Require the delegated result to identify evidence, changed paths, validations, and unresolved gaps.

Never hand off to an undeclared agent or use delegation to bypass a gate.
