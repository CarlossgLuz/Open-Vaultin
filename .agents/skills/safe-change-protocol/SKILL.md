---
name: safe-change-protocol
description: Plan and execute the smallest authorized engineering change with evidence, scope control, tests, rollback thinking, and Vaultin policy enforcement.
version: 1.0.0
source: vaultin-core
---

# Safe change protocol

1. Establish repository state, applicable instructions, current behavior, and acceptance criteria.
2. Confirm root cause before fixing a bug.
3. Define the smallest behavior/file scope and preserve unrelated user changes.
4. Define validation before editing; add rollback for data, infra, auth, release, or destructive-risk changes.
5. Use test-first development for behavior changes when practical.
6. Stop when new authority, secret access, destructive action, or material scope expansion would be required.
7. Run native validation proportional to risk and record exact results.
8. Review the final diff for unrelated work, secret exposure, contract drift, and rollback viability.

Never claim tests or deployment evidence that did not run.
