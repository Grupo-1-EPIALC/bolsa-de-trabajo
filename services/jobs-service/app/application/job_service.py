"""Casos de uso de ofertas y búsquedas de empresas.

Controllers delgados -> este servicio -> dominio <- infraestructura (AGENTS.md §2.1).
"""

import logging
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

from app.application.commands import JobDraft
from app.domain.auth import Principal
from app.domain.enums import JobStatus
from app.domain.errors import (
    ConflictError,
    InvalidInputError,
    NotFoundError,
    UnauthorizedError,
)
from app.domain.models import CompanySnapshot, JobOpportunity, WorkConditions
from app.domain.ports import Clock, CompanyDirectory, EventPublisher, IdGenerator, JobRepository
from app.domain.rules import (
    can_view,
    ensure_company_snapshot,
    ensure_owner,
    parse_status_filter,
    public_list_status,
    require_company,
    validate_job,
    with_visible_salary,
)

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 5
MAX_PAGE_SIZE = 200
_PATCHABLE_FIELDS = frozenset(
    {
        "title",
        "description",
        "responsibilities",
        "area",
        "seniority",
        "vacancies",
        "location",
        "work_conditions",
        "requirements",
        "benefits",
        "expires_at",
    }
)


@dataclass(frozen=True)
class JobPage:
    items: tuple[JobOpportunity, ...]
    total: int
    page: int
    size: int
    pages: int


class JobService:
    def __init__(
        self,
        repository: JobRepository,
        directory: CompanyDirectory,
        publisher: EventPublisher,
        clock: Clock,
        ids: IdGenerator,
        *,
        default_page_size: int = DEFAULT_PAGE_SIZE,
        max_page_size: int = MAX_PAGE_SIZE,
    ) -> None:
        self._repository = repository
        self._directory = directory
        self._publisher = publisher
        self._clock = clock
        self._ids = ids
        self._default_page_size = default_page_size
        self._max_page_size = max_page_size

    # ------------------------------------------------------------- lectura ---

    def get(self, principal: Principal, job_id: str) -> JobOpportunity:
        job = self._get_raw(job_id)
        if not can_view(job, principal):
            # No revelamos que existe una oferta cerrada de otra empresa.
            raise NotFoundError(f"Oferta '{job_id}' no encontrada", {"job_id": job_id})
        return with_visible_salary(job, principal)

    def list_jobs(
        self,
        principal: Principal,
        *,
        status_filter: str = JobStatus.ACTIVE.value,
        page: int = 1,
        size: int | None = None,
    ) -> JobPage:
        status = public_list_status(principal, status_filter)
        return self._list(
            principal,
            status=status,
            company_id=None,
            page=page,
            size=size,
            mask_salary=True,
        )

    def list_my_searches(
        self,
        principal: Principal,
        *,
        status_filter: str = JobStatus.ACTIVE.value,
        page: int = 1,
        size: int | None = None,
    ) -> JobPage:
        require_company(principal)
        status = parse_status_filter(status_filter)
        return self._list(
            principal,
            status=status,
            company_id=principal.subject,
            page=page,
            size=size,
            mask_salary=False,
        )

    # ------------------------------------------------------------ escritura ---

    def create(
        self, principal: Principal, draft: JobDraft, *, access_token: str | None
    ) -> JobOpportunity:
        require_company(principal)
        if not access_token:
            raise UnauthorizedError("No se pudo identificar la empresa para crear la oferta")

        now = self._now()
        # Validamos el payload ANTES de llamar a auth-service: un body inválido
        # responde 422 aclarado por campo, sin depender de que el upstream esté vivo
        # (y sin obligar a auth-service a procesar pedidos que ya son inválidos).
        provisional = JobOpportunity(
            id=self._ids.new_id(),
            company_id=principal.subject,
            company_snapshot=CompanySnapshot(
                name="", industry=None, size=None, logo_url=None
            ),  # placeholder: se completa con auth-service; `validate_job` no lo usa
            status=JobStatus.ACTIVE,
            title=draft.title,
            description=draft.description,
            responsibilities=tuple(draft.responsibilities),
            area=draft.area,
            seniority=draft.seniority,
            vacancies=draft.vacancies,
            location=draft.location,
            work_conditions=draft.work_conditions,
            requirements=draft.requirements,
            benefits=tuple(draft.benefits),
            created_at=now,
            updated_at=now,
            published_at=now,
            expires_at=_utc_or_none(draft.expires_at),
            version=1,
        )
        validate_job(provisional, now=now, check_expiry=True)
        snapshot = self._directory.snapshot_for(access_token)
        ensure_company_snapshot(snapshot)
        job = replace(provisional, company_snapshot=snapshot)
        self._repository.add(job)
        self._publish_created(job)
        return job

    def update(self, principal: Principal, job_id: str, patch: Mapping[str, Any]) -> JobOpportunity:
        job = self._get_raw(job_id)
        ensure_owner(principal, job)

        unknown = set(patch) - _PATCHABLE_FIELDS - {"status"}
        if unknown:
            raise InvalidInputError(
                "Hay campos que no se pueden modificar",
                {"fields": sorted(unknown)},
            )
        if not patch:
            raise InvalidInputError("No se enviaron campos para actualizar")

        now = self._now()
        updates: dict[str, Any] = {key: value for key, value in patch.items() if key != "status"}

        if "status" in patch:
            status = patch["status"]
            if status not in (None, JobStatus.ACTIVE):
                raise InvalidInputError(
                    "Para cerrar una oferta usá DELETE; PATCH sólo permite reabrir",
                    {"field": "status"},
                )
            if status == JobStatus.ACTIVE and job.status is JobStatus.CLOSED:
                updates["status"] = JobStatus.ACTIVE
                updates["published_at"] = now

        if "expires_at" in updates:
            updates["expires_at"] = _utc_or_none(updates["expires_at"])
        if updates.get("work_conditions") is None and "work_conditions" in updates:
            updates["work_conditions"] = WorkConditions()
        for collection in ("responsibilities", "benefits"):
            if collection in updates:
                updates[collection] = tuple(updates[collection])

        if not updates:
            # Reabrir una oferta que ya estaba activa es idempotente: 200 sin cambios.
            return job

        updated = replace(
            job,
            **updates,
            updated_at=now,
            version=job.version + 1,
        )
        validate_job(updated, now=now, check_expiry="expires_at" in updates)
        if not self._repository.update(updated, expected_version=job.version):
            # Alguien más editó mientras validábamos: pedimos releer la oferta
            # (409 + reintentar). Sin esto se perdía un cambio entre procesos.
            raise ConflictError(
                "La oferta fue modificada mientras la editabas; volvé a leerla y reintentá",
                {"job_id": job_id},
            )
        return updated

    def close(self, principal: Principal, job_id: str) -> JobOpportunity:
        job = self._get_raw(job_id)
        ensure_owner(principal, job)
        if job.status is JobStatus.CLOSED:
            return job
        now = self._now()
        closed = replace(
            job,
            status=JobStatus.CLOSED,
            updated_at=now,
            version=job.version + 1,
        )
        if not self._repository.update(closed, expected_version=job.version):
            # Si otra escritura ganó la carrera pero ya dejó la oferta cerrada,
            # el cierre sigue siendo idempotente; un cambio distinto es conflicto.
            fresh = self._get_raw(job_id)
            if fresh.status is JobStatus.CLOSED:
                return fresh
            raise ConflictError(
                "La oferta fue modificada mientras la cerrabas; volvé a leerla y reintentá",
                {"job_id": job_id},
            )
        return closed

    # ------------------------------------------------------------- helpers ---

    def _get_raw(self, job_id: str) -> JobOpportunity:
        job = self._repository.get(job_id)
        if job is None:
            raise NotFoundError(f"Oferta '{job_id}' no encontrada", {"job_id": job_id})
        return job

    def _list(
        self,
        principal: Principal,
        *,
        status: JobStatus | None,
        company_id: str | None,
        page: int,
        size: int | None,
        mask_salary: bool,
    ) -> JobPage:
        current_page = max(1, page)
        current_size = self._page_size(size)
        offset = (current_page - 1) * current_size
        items, total = self._repository.list(
            status=status,
            company_id=company_id,
            offset=offset,
            limit=current_size,
        )
        visible = (
            tuple(with_visible_salary(job, principal) for job in items)
            if mask_salary
            else tuple(items)
        )
        pages = (total + current_size - 1) // current_size
        return JobPage(
            items=visible,
            total=total,
            page=current_page,
            size=current_size,
            pages=pages,
        )

    def _page_size(self, size: int | None) -> int:
        if size is None:
            return self._default_page_size
        return max(1, min(size, self._max_page_size))

    def _now(self) -> datetime:
        now = self._clock.now()
        return now.replace(tzinfo=UTC) if now.tzinfo is None else now.astimezone(UTC)

    def _publish_created(self, job: JobOpportunity) -> None:
        """El alta no falla si n8n no está disponible (best-effort, AGENTS.md §4.3)."""
        try:
            self._publisher.job_created(job)
        except Exception:
            logger.exception("No se pudo publicar job.created para %s", job.id)


def _utc_or_none(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
