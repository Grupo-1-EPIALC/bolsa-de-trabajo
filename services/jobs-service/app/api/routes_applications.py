"""Postulaciones (`/api/v1/jobs/.../applications`). Controllers delgados."""

from typing import Any

from fastapi import APIRouter, Response, status

from app.api.deps import ContainerDep, PrincipalDep
from app.api.mappers import applicant_to_dict, student_application_to_dict

router = APIRouter(prefix="/api/v1/jobs", tags=["applications"])


@router.get("/applications/me", summary="Postulaciones del estudiante autenticado")
def my_applications(container: ContainerDep, principal: PrincipalDep) -> dict[str, Any]:
    items = [student_application_to_dict(item) for item in container.applications.mine(principal)]
    return {"items": items, "total": len(items)}


@router.post(
    "/{job_id}/applications",
    status_code=status.HTTP_201_CREATED,
    summary="Postularse a una oferta (estudiante). Repetirlo refresca el contacto: 200",
)
def apply(
    job_id: str, container: ContainerDep, principal: PrincipalDep, response: Response
) -> dict[str, Any]:
    result = container.applications.apply(principal, job_id, access_token=principal.access_token)
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return applicant_to_dict(result.application)


@router.delete(
    "/{job_id}/applications/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Retirar la postulación (estudiante). Idempotente",
)
def withdraw(job_id: str, container: ContainerDep, principal: PrincipalDep) -> Response:
    container.applications.withdraw(principal, job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{job_id}/applications",
    summary="Postulados a una oferta, con su contacto (empresa dueña, admin o servicio)",
)
def list_applicants(
    job_id: str, container: ContainerDep, principal: PrincipalDep
) -> dict[str, Any]:
    items = [
        applicant_to_dict(item) for item in container.applications.applicants(principal, job_id)
    ]
    return {"job_id": job_id, "items": items, "total": len(items)}
