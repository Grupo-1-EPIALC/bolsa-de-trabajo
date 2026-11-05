"""Repositorios en memoria (MVP).

Detrás de los puertos `RecommendationRepository` / `RecommendationRequestRepository`; se
reemplazan por la implementación en el schema `matching` de Postgres cuando se acuerde el ORM.
Los datos se pierden al reiniciar el contenedor.
"""

import threading

from app.domain.recommendations import (
    AiRecommendation,
    RecommendationMode,
    RecommendationRequest,
)
from app.domain.settings import RecommendationSettings


class InMemoryRecommendationRepository:
    def __init__(self) -> None:
        self._items: list[AiRecommendation] = []
        self._lock = threading.Lock()

    def save(self, recommendation: AiRecommendation) -> AiRecommendation:
        with self._lock:
            self._items.append(recommendation)
        return recommendation

    def _latest(
        self, mode: RecommendationMode, key_attr: str, key: str, group_attr: str
    ) -> list[AiRecommendation]:
        with self._lock:
            candidates = [r for r in self._items if r.mode is mode and getattr(r, key_attr) == key]
        latest: dict[str, AiRecommendation] = {}
        for rec in candidates:  # orden de inserción: el último pisa al anterior
            latest[getattr(rec, group_attr)] = rec
        return list(latest.values())

    def latest_for_profile(self, profile_id: str) -> list[AiRecommendation]:
        return self._latest(RecommendationMode.STUDENT, "profile_id", profile_id, "job_id")

    def latest_for_job(self, job_id: str) -> list[AiRecommendation]:
        return self._latest(RecommendationMode.COMPANY, "job_id", job_id, "profile_id")

    def all(self) -> list[AiRecommendation]:
        with self._lock:
            return list(self._items)


class InMemoryRecommendationRequestRepository:
    def __init__(self) -> None:
        self._items: dict[str, RecommendationRequest] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()

    def save(self, request: RecommendationRequest) -> RecommendationRequest:
        with self._lock:
            if request.id not in self._items:
                self._order.append(request.id)
            self._items[request.id] = request
        return request

    def get(self, request_id: str) -> RecommendationRequest | None:
        with self._lock:
            return self._items.get(request_id)

    def latest_for(self, mode: str, subject_id: str) -> RecommendationRequest | None:
        with self._lock:
            for request_id in reversed(self._order):
                req = self._items[request_id]
                if req.mode.value == mode and req.subject_id == subject_id:
                    return req
        return None


class InMemorySettingsRepository:
    """Arranca con los valores de `scoring_rules.yaml`; los cambios de un admin viven en memoria."""

    def __init__(self, initial: RecommendationSettings) -> None:
        self._current = initial
        self._lock = threading.Lock()

    def get(self) -> RecommendationSettings:
        with self._lock:
            return self._current

    def save(self, settings: RecommendationSettings) -> RecommendationSettings:
        with self._lock:
            self._current = settings
        return settings
