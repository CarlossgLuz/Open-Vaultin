from pathlib import Path

import yaml

from vaultin.routing.fallback import FallbackRouter
from vaultin.routing.jev import TaskInput


def test_routing_eval_cases_match_expected_core_agents() -> None:
    raw = yaml.safe_load((Path.cwd() / "evals/cases/routing.yaml").read_text(encoding="utf-8"))
    router = FallbackRouter()
    failures = []
    for case in raw["cases"]:
        actual = router.route(TaskInput(text=case["prompt"])).agents
        if actual != case["agents"]:
            failures.append((case["prompt"], case["agents"], actual))
    assert failures == []
