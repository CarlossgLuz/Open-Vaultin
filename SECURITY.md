# Security Policy

## Supported version

Vaultin is currently pre-1.0. Security fixes are applied to the active development line.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability that could expose credentials, private project knowledge, hook bypasses or unsafe synchronization behavior.

Use GitHub private vulnerability reporting when enabled for the repository, or contact the maintainer privately through the repository owner's published contact channel.

Include reproduction steps, affected component, expected impact and any relevant environment details. Do not include real secrets.

## Security model

Vaultin treats routing and authorization as separate concerns. JEV is advisory. Policy evaluation remains authoritative.

Local client hooks are not represented as a stronger security boundary than the host client actually provides.
