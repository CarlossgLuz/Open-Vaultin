from pathlib import Path

import yaml

from vaultin.models import ActionContext
from vaultin.policy.engine import PolicyEngine


def test_policy_eval_cases_match_expected_decisions() -> None:
    raw = yaml.safe_load((Path.cwd() / "evals/cases/policy.yaml").read_text(encoding="utf-8"))
    failures = []
    for case in raw["cases"]:
        decision = PolicyEngine.from_mapping(case["mapping"]).evaluate(
            ActionContext(action=case["action"], user_authorized=case["user_authorized"])
        )
        if decision.kind.value != case["expected"]:
            failures.append((case["name"], case["expected"], decision.kind.value))
    assert failures == []
