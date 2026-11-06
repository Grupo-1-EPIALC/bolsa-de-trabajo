"""Repositorios en memoria del perfil de empresa y su logo (tests y modo sin base)."""

import threading

from app.domain.company import CompanyProfile
from app.domain.ports import StoredLogo


class InMemoryCompanyProfileRepository:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, CompanyProfile] = {}

    def add(self, profile: CompanyProfile) -> None:
        with self._lock:
            self._items[profile.company_id] = profile

    def update(self, profile: CompanyProfile) -> None:
        with self._lock:
            self._items[profile.company_id] = profile

    def get_by_company(self, company_id: str) -> CompanyProfile | None:
        with self._lock:
            return self._items.get(company_id)

    def list(self, *, offset: int, limit: int) -> tuple[list[CompanyProfile], int]:
        with self._lock:
            ordered = sorted(self._items.values(), key=lambda p: p.id)
        return ordered[offset : offset + limit], len(ordered)


class InMemoryLogoStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, StoredLogo] = {}

    def save(self, company_id: str, logo: StoredLogo) -> None:
        with self._lock:
            self._items[company_id] = logo

    def get(self, company_id: str) -> StoredLogo | None:
        with self._lock:
            return self._items.get(company_id)

    def delete(self, company_id: str) -> None:
        with self._lock:
            self._items.pop(company_id, None)
