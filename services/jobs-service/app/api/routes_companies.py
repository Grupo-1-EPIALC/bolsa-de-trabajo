"""Endpoints de la empresa autenticada (`/api/v1/companies`)."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query

from app.api.deps import ContainerDep, PaginationDep, PrincipalDep
from app.api.mappers import page_to_dict

router = APIRouter(prefix="/api/v1/companies", tags=["companies"])


@router.get("/me/searches", summary="Búsquedas de la empresa autenticada")
def list_my_searches(
    container: ContainerDep,
    principal: PrincipalDep,
    pagination: PaginationDep,
    job_status: Annotated[Literal["active", "closed", "all"], Query(alias="status")] = "active",
) -> dict[str, Any]:
    page = container.jobs.list_my_searches(
        principal,
        status_filter=job_status,
        page=pagination.page,
        size=pagination.size,
    )
    return page_to_dict(page)
