# Getting started

## 1. Fork first

For personal use, fork Open-Vaultin to a **private** repository. Vaultin is intended to hold durable knowledge and project-vault metadata that may be private.

## 2. Configure your fork

Edit `vaultin.yaml` before installation:

```yaml
version: 1
repository: YOUR_GITHUB_USER/Open-Vaultin
project_vault_owner: YOUR_GITHUB_USER
project_vault_prefix: vault-
fail_closed: true
runtime_dir_name: .vaultin-runtime
```

## 3. Install

Windows:

```powershell
.\scripts\install.ps1
```

Linux:

```bash
bash scripts/install.sh
```

Vaultin is installed in editable mode inside its isolated venv. Updating the checkout therefore updates the implementation used by the hooks without leaving an old copied package behind.

## 4. Verify

```text
vaultinctl health
vaultinctl doctor
vaultinctl status
```

## 5. Enable Codex integration

Restart the client after installation, verify the Vaultin plugin is enabled, review/trust the local hook, then start a fresh session.

## 6. Optional JEV routing

Linux:

```bash
export TYPESAFE_API_KEY="..."
```

PowerShell:

```powershell
$env:TYPESAFE_API_KEY = "..."
```

JEV selects a typed route under a bounded timeout. Vaultin falls back deterministically if JEV is unavailable or uncertain. Policy authority never moves to JEV.

## 7. Privacy

Local runtime state lives under the configured runtime directory. Execution receipts are local under `memory/` and are not published by default.

Do not commit secrets, personal transcripts, private paths or private project notes to a public repository.
