---
name: memory-and-git-sync
description: Finalize an authorized mutation by curating durable knowledge, writing a concise receipt, committing canonical Vaultin memory, synchronizing project replicas, and recording verified Git evidence.
version: 1.0.0
source: vaultin-core
---

# Memory and Git sync

1. Confirm the execution is governed and the mutation/publication scope is authorized.
2. Promote only durable knowledge; keep ephemeral telemetry in the local runtime ledger.
3. Write/update the canonical project vault under `vaults/projects/<slug>/` before touching any replica.
4. Create the execution receipt with changed paths, validations, Git SHAs, decisions, and pending items.
5. Commit the smallest relevant canonical paths.
6. Project project-vault content into its private replica and verify both local/remote SHAs.
7. On network failure, persist `PENDING_SYNC` or `PARTIAL_SYNC`; never claim synchronization that did not happen.
8. Never force-push, rewrite history, or let replica content silently overwrite canonical Vaultin content.

This skill never grants Git publication authority by itself.
