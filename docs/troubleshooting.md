# Troubleshooting

Start with:

```text
vaultinctl doctor
```

Vaultin is designed to report blocked governance instead of silently repairing or weakening it.

## `vaultinctl health` returns `BLOCKED`

Read the failed check name and detail.

The health gate validates:

- `config`;
- `policy`;
- `workflow`;
- `agents`;
- `skills`;
- `ledger`.

Typical causes include a missing/invalid YAML file, an invalid registry/catalog entry, or an unusable runtime path.

Repair the named source instead of replacing canonical files with guessed defaults.

## `vaultinctl` is not found after installation

### Linux

The installer creates:

```text
~/.vaultin/bin/vaultinctl
~/.local/bin/vaultinctl
```

If your current shell does not include `~/.local/bin`, invoke the absolute path or update your shell PATH.

Governance hooks do not depend on shell PATH because the installer renders an absolute hook wrapper.

### Windows

The installer adds:

```text
%USERPROFILE%\.vaultin\bin
```

to the user PATH when needed.

Open a new shell if the current process has not picked up the updated user environment.

## Codex is not invoking Vaultin

Check:

1. the Vaultin plugin is installed and enabled;
2. the client was restarted after installation;
3. the local hook trust prompt was accepted;
4. `~/.codex/hooks.json` contains Vaultin lifecycle groups;
5. the hook command points to the rendered absolute wrapper;
6. the Vaultin root marker exists.

Then inspect:

```text
~/.vaultin/hook-errors.log
```

Hook exceptions are appended there with event name, exception type, and message.

## A new prompt is blocked by an old execution

Current Vaultin recovers an unfinished previous turn when a new `UserPromptSubmit` arrives, and `Interrupt` also releases the active execution. If you still see a message that an execution is already active, verify that the installed environment is not running stale code.

Re-run the installer once after upgrading from an older installation. Current installers use an editable package installation, so subsequent Git updates are consumed directly by the hook runtime.

Then restart the Codex client and run `vaultinctl doctor`.

## Hook exits with code 2

The hook entrypoint returns exit code 2 when an unhandled error prevents safe processing.

Inspect:

```text
~/.vaultin/hook-errors.log
```

and run:

```text
vaultinctl doctor
```

Do not convert a failing governance hook into a no-op just to make the client continue.

## Windows hook path contains whitespace

The current Codex Windows hook runner passes hook commands through `cmd.exe /C` in a way that does not safely support a quoted executable path with whitespace.

Vaultin detects this and raises an error.

Use a user/home/runtime location whose generated hook wrapper path does not contain whitespace, or wait for a host/runtime behavior that can safely execute quoted hook commands.

## A hook feels slow or appears stuck

Prompt-hook work is intentionally latency-bounded: project Git discovery and workspace probes use short subprocess timeouts, JEV is clamped to a 0.5–5 second budget, and workspace dirty-path discovery uses one porcelain-status probe instead of multiple sequential Git commands.

If the client still stalls, inspect `~/.vaultin/hook-errors.log`, run `vaultinctl doctor`, and verify the hook points to the current checkout.

## JEV is not being used

JEV requires:

```text
TYPESAFE_API_KEY
```

If the key is absent, empty, rejected, times out, returns malformed JSON, returns an invalid schema, or produces insufficient confidence for required routing decisions, Vaultin chooses the deterministic fallback router.

This is expected failover behavior.

A fallback route does not indicate that policy was bypassed.

## I want to know whether JEV or fallback routed the task

The typed route contains:

```text
source: jev | fallback
fallback_reason: <reason or null>
```

The fallback path records a reason such as missing API key, HTTP failure, schema failure, or low routing confidence.

## Pending synchronization

`vaultinctl status` prints:

```text
pending_sync: <count>
```

A non-zero value means synchronization work remains in the persistent queue.

Runtime states include:

- `PENDING_SYNC`: required publication did not complete;
- `PARTIAL_SYNC`: at least one required repository published and another did not;
- `RETRYING_SYNC`: a queued synchronization is being retried.

The queue is file-backed and survives process restart.

See [operations/recovery.md](operations/recovery.md).

## Replica divergence

Vaultin refuses to overwrite a project-vault replica when its trusted SHA no longer matches the local/remote repository state.

The error is intentional.

Do not force-copy the replica over the canonical Vaultin path.

Instead:

1. inspect the independent replica change;
2. decide whether it should be re-applied to the canonical project vault;
3. restore a known synchronized state;
4. retry synchronization through the governed path.

Canonical content lives under:

```text
vaults/projects/<slug>/
```

## MCP cannot read a path

`read_canonical` only permits canonical Vaultin areas.

It rejects:

- absolute paths;
- path traversal;
- files outside the allowed top-level surfaces;
- missing files.

This is expected behavior.

## MCP cannot write a note

`write_project_note` requires:

- a valid project slug;
- an existing canonical project vault;
- a safe relative path;
- a `.md` target.

It intentionally does not create arbitrary filesystem content.

## MCP write succeeds but nothing was pushed

Git publication is opt-in.

Set:

```text
VAULTIN_MCP_ALLOW_PUBLISH=1
```

and request `publish=true` only when publication is intended.

Without the environment opt-in, a publisher is not configured.

## Break-glass

Use only when governance recovery genuinely requires it:

```text
vaultinctl break-glass --reason "<reason>" --ttl-minutes 15
```

Break-glass is audited and expires.

Do not automate this command from an agent or use it as a permanent workaround for a broken health check.

## A session ended without a receipt

If an active execution exists when `SessionEnd` fires before normal finalization, Vaultin marks that execution as failed.

Check the runtime ledger/events and hook error log.

A missing successful receipt should not be interpreted as successful completion.

## Release-readiness checks

A green test suite is necessary but not sufficient for a trusted installation. Follow [operations/cutover.md](operations/cutover.md) and validate the real client lifecycle in the target environment.
