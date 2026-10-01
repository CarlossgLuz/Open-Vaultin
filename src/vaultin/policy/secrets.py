from typing import Any


class SecretPolicy:
    def __init__(self, project_policy: dict[str, Any]) -> None:
        self._project_policy = project_policy

    def allow_persistence(self, value_kind: str) -> bool:
        if value_kind in {"environment_reference", "credential_id", "secret_reference"}:
            return True
        secrets = self._project_policy.get("secrets", {})
        return bool(secrets.get("allow_vault_persistence", False))
