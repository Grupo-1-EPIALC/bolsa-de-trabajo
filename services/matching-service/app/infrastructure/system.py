"""Reloj e identificadores."""

import uuid
from datetime import UTC, datetime


class UtcClock:
    def iso_now(self) -> str:
        return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class UuidIdGenerator:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex[:12]}"
