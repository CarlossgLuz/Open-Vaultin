# Vaultin governance

Vaultin is the canonical governance and durable-knowledge plane for this repository.

- Treat `policies/`, `workflows/`, `agents/registry.yaml`, and `.agents/skills/` as governed inputs.
- Do not claim that a hook or adapter provides enforcement that the detected client surface cannot technically provide.
- Durable project knowledge belongs under `vaults/projects/<project-slug>/`; project vault replicas are not canonical editing targets.
- Final completion claims must come from execution evidence and list actual changed file paths.
- Never persist secret values unless the project has an explicit policy allowing it.
