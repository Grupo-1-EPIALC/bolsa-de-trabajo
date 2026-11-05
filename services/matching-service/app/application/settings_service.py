"""Caso de uso: consultar y ajustar la configuración de recomendaciones (sólo admin)."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from app.domain.auth import Principal, Role
from app.domain.errors import ForbiddenError, InvalidInputError
from app.domain.ports import Clock, SettingsRepository
from app.domain.settings import MAX_LIMIT, MIN_LIMIT, RecommendationSettings

EDITABLE_FIELDS = ("student_jobs_limit", "company_candidates_limit")


class SettingsService:
    def __init__(self, repository: SettingsRepository, clock: Clock) -> None:
        self._repo = repository
        self._clock = clock

    def get(self, principal: Principal) -> RecommendationSettings:
        if not principal.sees_everything:
            raise ForbiddenError("Sólo un administrador puede ver la configuración")
        return self._repo.get()

    def update(self, principal: Principal, changes: Mapping[str, Any]) -> RecommendationSettings:
        """Actualiza los campos enviados (PATCH semántico). Sólo usuarios `admin`."""
        if principal.role is not Role.ADMIN:
            raise ForbiddenError("Sólo un administrador puede cambiar la configuración")
        unknown = sorted(set(changes) - set(EDITABLE_FIELDS))
        if unknown:
            raise InvalidInputError("Campos no editables en la configuración", {"fields": unknown})
        if not changes:
            raise InvalidInputError("No se envió ningún campo para actualizar")
        updated = replace(
            self._repo.get(),
            **dict(changes),
            updated_at=self._clock.iso_now(),
            updated_by=principal.subject,
        )
        return self._repo.save(updated)


def settings_to_dict(settings: RecommendationSettings) -> dict[str, Any]:
    return {
        "student_jobs_limit": settings.student_jobs_limit,
        "company_candidates_limit": settings.company_candidates_limit,
        "limits": {"min": MIN_LIMIT, "max": MAX_LIMIT},
        "updated_at": settings.updated_at,
        "updated_by": settings.updated_by,
    }
