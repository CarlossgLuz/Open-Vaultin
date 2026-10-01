# Installation

Vaultin targets Python 3.11+ on Windows and Linux.

Before installation, configure `repository` and `project_vault_owner` in `vaultin.yaml` for your own fork.

## Windows

```powershell
.\scripts\install.ps1
```

## Linux

```bash
bash scripts/install.sh
```

The installer:

- creates a dedicated venv under the user Vaultin state directory;
- installs the checkout in editable mode;
- records the canonical root;
- installs and enables the local Codex plugin;
- registers the personal plugin marketplace in `~/.agents/plugins/marketplace.json`;
- merges Vaultin hooks without clobbering unrelated hooks;
- invalidates only the Vaultin plugin cache;
- runs `vaultinctl health`.

After the first install or a material hook definition change, restart the client and perform the **one-time trust review** for the local Vaultin hook when prompted. Vaultin does not bypass the client's trust boundary.

A blocked health result is a blocker, not a warning to bypass.


## Runtime source pinning

The installed wrappers prepend the active checkout's `src/` directory to
`PYTHONPATH` before loading Vaultin. This guarantees that Codex hooks execute
the code from the repository recorded in `~/.vaultin/root`, not a stale package
copy left inside the virtual environment.

The installer verifies the resolved `vaultin.__file__` path and aborts if the
runtime is not being imported from that checkout. After updating Vaultin, rerun
the installer once if the wrapper itself changed, then restart the Codex/ChatGPT
client.
