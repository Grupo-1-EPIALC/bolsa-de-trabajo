"""Repositorio en memoria (tests y modo sin `DATABASE_URL`)."""

import threading

from app.domain.profile import StudentProfile


class InMemoryProfileRepository:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, StudentProfile] = {}

    def add(self, profile: StudentProfile) -> None:
        with self._lock:
            self._items[profile.id] = profile

    def update(self, profile: StudentProfile) -> None:
        with self._lock:
            self._items[profile.id] = profile

    def get(self, profile_id: str) -> StudentProfile | None:
        with self._lock:
            return self._items.get(profile_id)

    def get_by_user(self, user_id: str) -> StudentProfile | None:
        with self._lock:
            return next((p for p in self._items.values() if p.user_id == user_id), None)

    def list(self, *, offset: int, limit: int) -> tuple[list[StudentProfile], int]:
        with self._lock:
            ordered = sorted(self._items.values(), key=lambda p: p.id)
        return ordered[offset : offset + limit], len(ordered)

    def count(self) -> int:
        with self._lock:
            return len(self._items)
