from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from typing import Callable
from uuid import uuid4

from filelock import FileLock
from pydantic import BaseModel


class BreakGlassToken(BaseModel):
    id: str
    reason: str
    activated_at: datetime
    expires_at: datetime
    status: str = "active"


class BreakGlassAuditEvent(BaseModel):
    token_id: str
    action: str
    reason: str
    at: datetime


class BreakGlassManager:
    def __init__(self, root: Path, *, now: Callable[[], datetime] | None = None) -> None:
        self.root = Path(root)
        self.runtime = self.root / ".vaultin-runtime"
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.tokens_path = self.runtime / "break-glass.json"
        self.audit_path = self.runtime / "break-glass-audit.jsonl"
        self.lock = FileLock(str(self.tokens_path) + ".lock")
        self._now = now or (lambda: datetime.now(UTC))

    def _load_tokens_unlocked(self) -> dict[str, BreakGlassToken]:
        if not self.tokens_path.exists():
            return {}
        raw = json.loads(self.tokens_path.read_text(encoding="utf-8"))
        return {key: BreakGlassToken.model_validate(value) for key, value in raw.items()}

    def _save_tokens_unlocked(self, tokens: dict[str, BreakGlassToken]) -> None:
        temp = self.tokens_path.with_suffix(".json.tmp")
        payload = {key: token.model_dump(mode="json") for key, token in tokens.items()}
        temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(self.tokens_path)

    def _append_audit_unlocked(self, event: BreakGlassAuditEvent) -> None:
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json() + "\n")

    def activate(self, *, reason: str, ttl_minutes: int) -> BreakGlassToken:
        reason = reason.strip()
        if not reason:
            raise ValueError("reason is required")
        if ttl_minutes <= 0:
            raise ValueError("ttl_minutes must be positive")
        now = self._now()
        token = BreakGlassToken(
            id=f"bg_{uuid4().hex}",
            reason=reason,
            activated_at=now,
            expires_at=now + timedelta(minutes=ttl_minutes),
        )
        with self.lock:
            tokens = self._load_tokens_unlocked()
            tokens[token.id] = token
            self._save_tokens_unlocked(tokens)
            self._append_audit_unlocked(
                BreakGlassAuditEvent(token_id=token.id, action="activated", reason=reason, at=now)
            )
        return token

    def is_active(self, token_id: str) -> bool:
        with self.lock:
            tokens = self._load_tokens_unlocked()
            token = tokens.get(token_id)
            if token is None or token.status != "active":
                return False
            now = self._now()
            if now >= token.expires_at:
                expired = token.model_copy(update={"status": "expired"})
                tokens[token_id] = expired
                self._save_tokens_unlocked(tokens)
                self._append_audit_unlocked(
                    BreakGlassAuditEvent(token_id=token.id, action="expired", reason=token.reason, at=now)
                )
                return False
            return True

    def audit_events(self, token_id: str) -> list[BreakGlassAuditEvent]:
        if not self.audit_path.exists():
            return []
        events: list[BreakGlassAuditEvent] = []
        for line in self.audit_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = BreakGlassAuditEvent.model_validate_json(line)
            if event.token_id == token_id:
                events.append(event)
        return events
