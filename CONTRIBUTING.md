# Contributing

Contributions are welcome.

## Development setup

```bash
python -m pip install -e ".[dev]"
pytest
```

## Pull requests

- keep changes scoped;
- include tests for behavioral changes;
- preserve Windows and Linux compatibility;
- do not weaken fail-closed policy behavior without an explicit design change;
- do not add personal memory, credentials, private repository names or environment-specific paths;
- document new environment variables or configuration fields.

## Hooks and runtime

Lifecycle changes must cover interrupted turns, duplicate prompt delivery, orphan recovery and Stop behavior. A hook must not create a continuation loop or leave the next prompt permanently blocked.

## Security

For vulnerabilities, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.
