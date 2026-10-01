from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from vaultin.runtime.break_glass import BreakGlassManager


class FakeClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 9, 25, 18, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.value

    def advance(self, *, minutes: int) -> None:
        self.value += timedelta(minutes=minutes)


def test_break_glass_requires_explicit_reason(tmp_path: Path) -> None:
    manager = BreakGlassManager(tmp_path)
    with pytest.raises(ValueError, match="reason is required"):
        manager.activate(reason="", ttl_minutes=15)


def test_break_glass_expires_and_is_audited(tmp_path: Path) -> None:
    clock = FakeClock()
    manager = BreakGlassManager(tmp_path, now=clock.now)
    token = manager.activate(reason="repair corrupted local policy", ttl_minutes=15)
    assert manager.is_active(token.id)
    clock.advance(minutes=16)
    assert not manager.is_active(token.id)
    events = manager.audit_events(token.id)
    assert events[0].reason == "repair corrupted local policy"
    assert any(event.action == "expired" for event in events)


def test_break_glass_ttl_must_be_positive(tmp_path: Path) -> None:
    manager = BreakGlassManager(tmp_path)
    with pytest.raises(ValueError, match="ttl_minutes must be positive"):
        manager.activate(reason="repair", ttl_minutes=0)
