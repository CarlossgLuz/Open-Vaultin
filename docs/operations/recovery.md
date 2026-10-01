# Vaultin recovery

Vaultin is designed to fail visibly rather than silently relax governance.

## Health failure

Run `vaultinctl doctor`. Repair the named configuration, registry, workflow, or adapter problem; do not replace canonical files with guessed defaults.

## Pending or partial Git synchronization

`PENDING_SYNC` means required remotes were not published. `PARTIAL_SYNC` means at least one required remote succeeded and another did not. The file-backed sync queue survives process restart. Reconciliation must retry only the queued repository/SHA pair.

## Replica divergence

If a `vault-<project>` replica changed independently, Vaultin raises `ReplicaDivergence`. The replica must be inspected and reconciled deliberately. Replica content never wins automatically over `Vaultin/vaults/projects/<project>`.

## Break-glass

Use break-glass only from the explicit CLI with a reason and bounded TTL. It is audited and expires automatically. It must not be auto-activated by an agent.

## Failed runtime update

The release manager keeps the last healthy version. A failed post-update healthcheck returns the rollback target and sets `auto_update_suspended`; automatic updates remain suspended until a healthy repair is recorded.
