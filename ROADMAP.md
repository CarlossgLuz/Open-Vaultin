# Roadmap

Open-Vaultin is currently an early V1 / pre-1.0 project. The roadmap prioritizes reliability and portability before expanding the feature surface.

## Current baseline

Implemented today:

- local-first execution ledger;
- strict repository configuration;
- policy engine and precedence rules;
- agent and skill registries;
- Codex lifecycle hooks;
- interrupted/orphaned execution recovery;
- bounded Git and JEV latency;
- compact validated routing context;
- deterministic routing fallback;
- project discovery;
- canonical project vaults;
- replica divergence protection;
- persistent synchronization queue;
- narrow MCP server;
- Windows and Linux installers;
- Windows/Linux CI;
- security, contribution and support documentation.

## Near-term priorities

### 0.1.x — stabilization

- expand real-client lifecycle validation;
- improve diagnostics around hook/runtime mismatch;
- harden upgrade and rollback behavior;
- extend regression coverage for interrupted and duplicate lifecycle events;
- improve packaging/distribution ergonomics;
- document more real-world deployment patterns.

### 0.2 — multi-client maturity

- validate secondary-client integrations against their real capability boundaries;
- improve adapter capability reporting;
- expand MCP interoperability testing;
- formalize compatibility documentation by client/version.

### Later

Potential areas, subject to design review:

- richer observability and execution inspection;
- safer project-vault provisioning workflows;
- configurable knowledge retention policies;
- stronger schema/version migration tooling;
- improved release/update automation;
- additional typed routing providers.

## Non-goals

Open-Vaultin does not intend to:

- pretend local hooks are an OS-level security sandbox;
- give an LLM or router policy authority;
- automatically publish private execution memory;
- silently resolve replica divergence;
- hide degraded governance states to keep an AI client moving.

## Contributing to the roadmap

Open focused issues that describe:

1. the concrete workflow/problem;
2. current behavior;
3. proposed behavior;
4. security/privacy implications;
5. Windows/Linux or client compatibility considerations.

See [CONTRIBUTING.md](CONTRIBUTING.md).
