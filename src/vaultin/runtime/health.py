from __future__ import annotations

from pathlib import Path

import vaultin
from typing import Literal

from pydantic import BaseModel
import yaml

from vaultin.agents.registry import AgentRegistry
from vaultin.config import load_settings
from vaultin.ledger.store import LedgerStore
from vaultin.paths import VaultinPaths
from vaultin.skills.catalog import SkillCatalog
from vaultin.workflow.state_machine import StateMachine


class HealthCheck(BaseModel):
    name: str
    status: Literal["PASS", "BLOCKED"]
    detail: str


class HealthReport(BaseModel):
    status: Literal["PASS", "BLOCKED"]
    checks: list[HealthCheck]


class HealthChecker:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def run(self, *, ledger_timeout_seconds: float = 5.0) -> HealthReport:
        checks: list[HealthCheck] = []

        def check(name: str, fn) -> None:
            try:
                fn()
                checks.append(HealthCheck(name=name, status="PASS", detail="ok"))
            except Exception as exc:
                checks.append(HealthCheck(name=name, status="BLOCKED", detail=str(exc)))

        check("config", lambda: load_settings(self.root))

        def runtime_source() -> None:
            expected = (self.root / "src" / "vaultin").resolve()
            # Lightweight fixtures and packaged consumers may not expose a
            # source checkout. When a checkout is present, however, the active
            # module must come from it; otherwise hooks may be running stale
            # site-packages code after the repository was updated.
            if not expected.is_dir():
                return
            module_file = getattr(vaultin, "__file__", None)
            if not module_file:
                raise RuntimeError("active Vaultin module path is unavailable")
            actual = Path(module_file).resolve()
            try:
                actual.relative_to(expected)
            except ValueError as exc:
                raise RuntimeError(
                    f"active Vaultin runtime is outside configured checkout: {actual}"
                ) from exc

        check("runtime-source", runtime_source)

        def policy() -> None:
            path = self.root / "policies" / "core.yaml"
            if not path.is_file():
                raise FileNotFoundError("policies/core.yaml not found")
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("policies/core.yaml must contain a mapping")

        check("policy", policy)
        check("workflow", lambda: StateMachine.default(self.root))
        check("agents", lambda: AgentRegistry.load(self.root))
        check("skills", lambda: SkillCatalog.load(self.root))

        def ledger() -> None:
            paths = VaultinPaths.from_root(self.root)
            LedgerStore(paths.ledger_db, timeout_seconds=ledger_timeout_seconds)

        check("ledger", ledger)
        overall = "PASS" if all(item.status == "PASS" for item in checks) else "BLOCKED"
        return HealthReport(status=overall, checks=checks)
