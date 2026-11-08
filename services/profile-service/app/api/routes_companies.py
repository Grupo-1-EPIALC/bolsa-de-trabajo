"""Endpoints del perfil de empresa (`/api/v1/profiles/companies`).

Van bajo `/profiles/` porque el gateway envía `/api/v1/companies/` a jobs-service.
Contrato para el front: `contracts/profile.md` (parte B).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Body, File, Query, Response, UploadFile, status

from app.api.deps import ContainerDep, PrincipalDep
from app.api.schemas_company import CompanyProfilePatch
from app.domain.errors import InvalidLogoError

router = APIRouter(prefix="/api/v1/profiles/companies", tags=["company-profiles"])


@router.get(
    "/me", summary="Perfil de mi empresa con su completitud (las búsquedas están en jobs-service)"
)
def get_my_company(container: ContainerDep, principal: PrincipalDep) -> dict[str, Any]:
    return container.companies.get_mine(principal)


@router.post(
    "/me",
    status_code=status.HTTP_201_CREATED,
    summary="Crear el perfil de mi empresa (se precarga con los datos de auth-service)",
)
def create_my_company(
    container: ContainerDep,
    principal: PrincipalDep,
    body: Annotated[CompanyProfilePatch | None, Body()] = None,
) -> dict[str, Any]:
    return container.companies.create_mine(principal, body.changes() if body else None)


@router.patch("/me", summary="Guardar secciones del perfil de mi empresa")
def update_my_company(
    container: ContainerDep, principal: PrincipalDep, body: CompanyProfilePatch
) -> dict[str, Any]:
    return container.companies.update_mine(principal, body.changes())


@router.put("/me/logo", summary="Subir o reemplazar el logo (PNG, JPEG o WebP · máx. 1 MB)")
async def upload_my_logo(
    container: ContainerDep,
    principal: PrincipalDep,
    file: Annotated[UploadFile, File(description="PNG, JPEG o WebP · máx. 1 MB")],
) -> dict[str, Any]:
    limit = container.settings.logo_max_kb * 1024
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise InvalidLogoError(
            f"El logo supera el máximo de {container.settings.logo_max_kb} KB",
            {"max_bytes": limit},
        )
    return container.companies.upload_logo(principal, content)


@router.delete(
    "/me/logo", status_code=status.HTTP_204_NO_CONTENT, summary="Quitar el logo de mi empresa"
)
def delete_my_logo(container: ContainerDep, principal: PrincipalDep) -> Response:
    container.companies.delete_logo(principal)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", summary="[interno] Perfiles de empresa (service o admin)")
def list_companies(
    container: ContainerDep,
    principal: PrincipalDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    page: Annotated[int, Query(ge=1)] = 1,
) -> dict[str, Any]:
    return container.companies.list_profiles(principal, limit=limit, page=page)


@router.get(
    "/{company_id}",
    summary="Perfil de una empresa (público para estudiantes; con `snapshot` para servicios)",
)
def get_company(
    company_id: str, container: ContainerDep, principal: PrincipalDep
) -> dict[str, Any]:
    return container.companies.get_profile(principal, company_id)


@router.get(
    "/{company_id}/logo",
    response_class=Response,
    summary="Logo de la empresa (público, para usar en <img>)",
    responses={200: {"content": {"image/png": {}, "image/jpeg": {}, "image/webp": {}}}},
)
def get_company_logo(company_id: str, container: ContainerDep) -> Response:
    logo = container.companies.get_logo(company_id)
    return Response(
        content=logo.content,
        media_type=logo.mime_type,
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'",
        },
    )
