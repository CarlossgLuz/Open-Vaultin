# Release readiness

Before treating an installation as trusted:

1. `vaultinctl health` passes.
2. Unit/integration/behavioral tests pass on the target platform.
3. A fresh client session exercises SessionStart, prompt routing, policy gating, Stop and Interrupt.
4. A failed or interrupted turn does not block the next prompt.
5. JEV failure falls back without changing policy authority.
6. Local execution memory remains local unless publication is explicitly enabled.
7. Project-vault synchronization and divergence protection are validated before automatic publication.
8. Repository branch protection and CI requirements are enabled.

Before publishing any repository, verify it contains no personal memory, runtime state, credentials, private project notes, user-specific paths or migrated environment knowledge.
