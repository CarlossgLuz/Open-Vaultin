from vaultin.policy.secrets import SecretPolicy


def test_missing_project_secret_policy_denies_persistence() -> None:
    policy = SecretPolicy(project_policy={})
    assert policy.allow_persistence("credential_value") is False


def test_explicit_project_secret_policy_can_override_default() -> None:
    policy = SecretPolicy(project_policy={
        "secrets": {"allow_vault_persistence": True}
    })
    assert policy.allow_persistence("credential_value") is True
