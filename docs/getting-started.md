# Getting started

The [README installation guide](../README.md#install-and-integrate-step-by-step) is the authoritative end-to-end walkthrough. Follow it in order for:

1. Prerequisites and an independent private copy (public GitHub forks cannot be private).
2. The exact `vaultin.yaml` fields to edit.
3. Obtaining a TypeSafe key and setting `TYPESAFE_API_KEY` on Windows or Linux, including persistence and process inheritance.
4. Installing the Codex plugin/hooks and checking the core runtime.
5. Starting a real session in an application repository and inspecting the routing ledger.
6. Optional GitHub provisioning, secondary-client MCP setup, updates and disabling the integration.

Do not put secrets into YAML. Vaultin does not automatically load `.env`. Core health checks do not validate the TypeSafe API key or prove live-client hook execution.

Detailed references: [Configuration](configuration.md), [Client integrations](client-integrations.md), [Installation](operations/install.md), [Troubleshooting](troubleshooting.md).
