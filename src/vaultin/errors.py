class VaultinError(RuntimeError):
    """Base Vaultin runtime error."""


class ConfigError(VaultinError):
    """Raised when canonical Vaultin configuration is invalid."""


class GovernanceBlocked(VaultinError):
    """Raised when a required governance control denies or cannot validate execution."""
