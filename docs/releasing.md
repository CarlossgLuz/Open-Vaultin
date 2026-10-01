# Release process

Open-Vaultin uses semantic versioning for runtime releases.

The release workflow is intentionally **manual**.

## Before a release

Confirm that:

1. the target commit is on `main`;
2. CI is green on Windows and Linux;
3. unit, integration and behavioral evals pass;
4. `vaultinctl health --root .` passes;
5. public documentation matches the runtime behavior;
6. no personal memory, credentials, private paths or proprietary project knowledge are present.

## Triggering a release

Use the GitHub Actions workflow:

```text
Vaultin Release
```

The workflow is triggered with `workflow_dispatch`.

It:

1. installs the development dependencies;
2. runs the CI-compatible test suite;
3. classifies the runtime change;
4. calculates the next semantic version;
5. updates `VERSION`, `pyproject.toml` and `CHANGELOG.md`;
6. creates the release commit;
7. creates the Git tag;
8. publishes the GitHub Release.

## Version classification

The current workflow interprets the latest commit message as:

- breaking indicator / `!` -> major;
- `feat...` -> minor;
- other runtime changes -> patch.

Knowledge-only or non-runtime changes may result in no runtime release depending on the release manager classification.

## Pre-1.0 note

Open-Vaultin is currently pre-1.0. Compatibility guarantees are intentionally conservative until the public interfaces and live-client integrations mature.
