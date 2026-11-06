"""Endpoints de ofertas (`/api/v1/jobs`). Controllers delgados."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query, Response, status

from app.api.deps import ContainerDep, PaginationDep, PrincipalDep
from app.api.mappers import job_to_dict, page_to_dict, to_draft, to_patch
from app.api.schemas import JobCreate, JobUpdate

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("", summary="Lista ofertas paginadas")
def list_jobs(
    container: ContainerDep,
    principal: PrincipalDep,
    pagination: PaginationDep,
    job_status: Annotated[Literal["active", "closed", "all"], Query(alias="status")] = "active",
) -> dict[str, Any]:
    page = container.jobs.list_jobs(
        principal,
        status_filter=job_status,
        page=pagination.page,
        size=pagination.size,
    )
    return page_to_dict(page)


@router.post("", status_code=status.HTTP_201_CREATED, summary="Crea una oferta (empresa)")
def create_job(
    body: JobCreate,
    container: ContainerDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    job = container.jobs.create(
        principal,
        to_draft(body),
        access_token=principal.access_token,
    )
    return job_to_dict(job)


@router.get("/{job_id}", summary="Detalle de una oferta")
def get_job(job_id: str, container: ContainerDep, principal: PrincipalDep) -> dict[str, Any]:
    return job_to_dict(container.jobs.get(principal, job_id))


@router.patch("/{job_id}", summary="Edita o reabre una oferta (empresa dueña)")
def update_job(
    job_id: str,
    body: JobUpdate,
    container: ContainerDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    return job_to_dict(container.jobs.update(principal, job_id, to_patch(body)))


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Cierra una oferta")
def close_job(job_id: str, container: ContainerDep, principal: PrincipalDep) -> Response:
    container.jobs.close(principal, job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
