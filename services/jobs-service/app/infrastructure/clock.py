"""Reloj e IDs del sistema."""

from datetime import UTC, datetime
from uuid import uuid4


class UtcClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class UuidIdGenerator:
    def new_id(self) -> str:
        return str(uuid4())
