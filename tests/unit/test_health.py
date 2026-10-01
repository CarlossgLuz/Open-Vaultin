from pathlib import Path

from vaultin.runtime.health import HealthChecker


def _source_check(report):
    return next(item for item in report.checks if item.name == "runtime-source")


def test_runtime_source_check_passes_for_active_checkout() -> None:
    report = HealthChecker(Path.cwd()).run()
    assert _source_check(report).status == "PASS"


def test_runtime_source_check_detects_stale_checkout(tmp_path: Path) -> None:
    (tmp_path / "src" / "vaultin").mkdir(parents=True)
    report = HealthChecker(tmp_path).run()
    check = _source_check(report)
    assert check.status == "BLOCKED"
    assert "outside configured checkout" in check.detail
