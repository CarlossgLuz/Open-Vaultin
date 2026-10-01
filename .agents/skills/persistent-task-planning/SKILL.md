---
name: persistent-task-planning
description: Keep a recoverable execution plan for complex, multi-step, high-risk, or multi-file work using the Vaultin ledger, explicit acceptance criteria, risks, validations, and rulings.
version: 1.0.0
source: vaultin-core
---

# Persistent task planning

1. Start from a valid Vaultin execution context.
2. Record objective, acceptance criteria, allowed scope, evidence, risks, validation, rollback, and external dependencies.
3. Update the ledger after material discovery, failed attempts, scope rulings, and state transitions.
4. Re-evaluate the plan before materially expanding scope or changing architecture.
5. Keep credentials, raw prompts, sensitive logs, and transient tool payloads out of durable knowledge.
6. Finish only when the execution receipt and final response are backed by recorded evidence.

Do not use this skill for trivial one-step/read-only questions.
