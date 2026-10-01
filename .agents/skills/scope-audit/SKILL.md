---
name: scope-audit
description: Audit a material plan or diff and remove work that does not trace to acceptance criteria, evidence, or risk mitigation. Use for broad, multi-domain, refactoring, or high-risk changes.
version: 1.0.0
source: vaultin-core
---

# Scope audit

1. Receive objective, acceptance criteria, current plan/diff, and identified risks.
2. Justify every changed file and dependency by requirement or risk mitigation.
3. Remove unrelated refactors, dependencies, documentation churn, agent hops, and validation work.
4. Flag unauthorized production access, destructive actions, or policy changes.
5. Return one outcome: `approved`, `reduce_scope`, or `blocked`, with evidence-backed reasons.

This is a read-only gate; it does not choose architecture or expand authority.
