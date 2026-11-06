"""Reloj e ids reales."""

import uuid
from datetime import UTC, datetime


class UtcClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class UuidIdGenerator:
    def new_profile_id(self) -> str:
        return f"prof-{uuid.uuid4().hex[:12]}"

    def new_company_id(self) -> str:
        return f"comp-{uuid.uuid4().hex[:12]}"
