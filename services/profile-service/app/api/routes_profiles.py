"""Endpoints REST del perfil (`/api/v1/profiles`). Controllers delgados: la lógica está en
`ProfileService`. Contrato para el front: `contracts/profile.md` (parte A).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Body, File, Query, Response, UploadFile, status

from app.api.deps import ContainerDep, PrincipalDep
from app.api.schemas import CvDesignChoice, ProfilePatch
from app.domain.errors import InvalidCvFileError

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])

_CHUNK = 1024 * 1024


@router.get("/me", summary="Mi perfil (estudiante) con el estado de completitud")
def get_my_profile(container: ContainerDep, principal: PrincipalDep) -> dict[str, Any]:
    return container.profiles.get_mine(principal)


@router.post(
    "/me",
    status_code=status.HTTP_201_CREATED,
    summary="Crear mi perfil a mano (borrador). El email se precarga desde auth-service",
)
def create_my_profile(
    container: ContainerDep,
    principal: PrincipalDep,
    body: Annotated[ProfilePatch | None, Body()] = None,
) -> dict[str, Any]:
    return container.profiles.create_mine(principal, body.changes() if body else None)


@router.patch("/me", summary="Guardar secciones de mi perfil (cada sección se reemplaza completa)")
def update_my_profile(
    container: ContainerDep, principal: PrincipalDep, body: ProfilePatch
) -> dict[str, Any]:
    return container.profiles.update_mine(principal, body.changes())


@router.post(
    "/me/cv",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Subir mi CV (multipart) y extraer los datos con IA en segundo plano (WF-01)",
)
async def upload_my_cv(
    container: ContainerDep,
    principal: PrincipalDep,
    file: Annotated[UploadFile, File(description=".pdf, .docx, .doc o .md · máx. 5 MB")],
) -> dict[str, Any]:
    limit = container.settings.cv_max_size_mb * 1024 * 1024
    content = bytearray()
    while chunk := await file.read(_CHUNK):
        content.extend(chunk)
        if len(content) > limit:
            max_mb = container.settings.cv_max_size_mb
            raise InvalidCvFileError(
                f"El archivo supera el tamaño máximo permitido ({max_mb} MB).",
                details={"max_bytes": limit},
            )
    return container.profiles.start_cv_extraction(
        principal,
        filename=file.filename or "cv",
        content=bytes(content),
        mime_type=file.content_type or "",
    )


@router.get("/me/cv/jobs/{job_id}", summary="Progreso y resultado de la extracción de mi CV")
def get_my_cv_job(job_id: str, container: ContainerDep, principal: PrincipalDep) -> dict[str, Any]:
    return container.profiles.get_cv_job(principal, job_id)


@router.get("/me/cv-suggestions", summary="Últimas sugerencias de la IA sobre mi CV (borrador)")
def get_my_cv_suggestions(container: ContainerDep, principal: PrincipalDep) -> dict[str, Any]:
    return container.profiles.get_suggestions(principal)


@router.delete(
    "/me/cv-suggestions",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Descartar las sugerencias de la IA",
)
def discard_my_cv_suggestions(container: ContainerDep, principal: PrincipalDep) -> Response:
    container.profiles.discard_suggestions(principal)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


LayoutQuery = Annotated[
    str | None,
    Query(
        description="Forzar un diseño del catálogo (cronologico, primer_empleo, competencias). "
        "Sin este parámetro se usa el que rige en GET /me/cv-design."
    ),
]


@router.get(
    "/me/cv-design",
    summary="Diseño de mi CV: el que rige, el elegido por reglas, el sugerido por IA y el catálogo",
)
def get_my_cv_design(container: ContainerDep, principal: PrincipalDep) -> dict[str, Any]:
    return container.cv_designs.view(principal)


@router.post(
    "/me/cv-design/requests",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Pedir a la IA (WF-07) el diseño de CV más adecuado a mi contenido, en segundo plano",
)
def request_my_cv_design(container: ContainerDep, principal: PrincipalDep) -> dict[str, Any]:
    return container.cv_designs.request_ai(principal)


@router.put(
    "/me/cv-design",
    summary="Elegir el diseño de mi CV (layout: null vuelve a la elección automática)",
)
def choose_my_cv_design(
    container: ContainerDep, principal: PrincipalDep, body: CvDesignChoice
) -> dict[str, Any]:
    return container.cv_designs.choose(principal, body.layout)


def _download(
    container: ContainerDep,
    principal: PrincipalDep,
    fmt: str,
    inline: bool,
    layout: str | None = None,
) -> Response:
    generated = container.profiles.generate_cv(principal, fmt, layout)
    disposition = "inline" if inline else "attachment"
    return Response(
        content=generated.file.content,
        media_type=generated.file.media_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{generated.filename}"',
            "Cache-Control": "no-store",
            "X-Cv-Layout": generated.layout,
        },
    )


@router.get(
    "/me/cv.pdf",
    response_class=Response,
    summary="Descargar un CV nuevo en PDF generado con mis datos (IA friendly)",
    responses={200: {"content": {"application/pdf": {}}}},
)
def download_cv_pdf(
    container: ContainerDep,
    principal: PrincipalDep,
    inline: Annotated[bool, Query(description="true = abrir en el navegador")] = False,
    layout: LayoutQuery = None,
) -> Response:
    return _download(container, principal, "pdf", inline, layout)


@router.get(
    "/me/cv.docx",
    response_class=Response,
    summary="Descargar un CV nuevo en DOCX (Word) generado con mis datos",
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {}
            }
        }
    },
)
def download_cv_docx(
    container: ContainerDep, principal: PrincipalDep, layout: LayoutQuery = None
) -> Response:
    return _download(container, principal, "docx", False, layout)


@router.get(
    "/me/cv.html",
    response_class=Response,
    summary="Vista previa en HTML del CV que se va a generar",
    responses={200: {"content": {"text/html": {}}}},
)
def preview_cv_html(
    container: ContainerDep, principal: PrincipalDep, layout: LayoutQuery = None
) -> Response:
    return _download(container, principal, "html", True, layout)


@router.get("", summary="[interno] Pool de perfiles para matching / mcp-tools (service o admin)")
def list_profiles(
    container: ContainerDep,
    principal: PrincipalDep,
    skills: Annotated[str | None, Query(description="Competencias separadas por coma")] = None,
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
    size: Annotated[int, Query(ge=1, le=200)] = 50,
    page: Annotated[int, Query(ge=1)] = 1,
    include_all: Annotated[
        bool, Query(description="Incluir borradores, ocultos y quienes no buscan")
    ] = False,
) -> dict[str, Any]:
    wanted = [s.strip() for s in (skills or "").split(",") if s.strip()]
    return container.profiles.list_profiles(
        principal,
        skills=wanted,
        limit=limit or size,
        page=page,
        include_all=include_all,
    )


@router.get("/{profile_id}", summary="Perfil por id (vista según rol: servicio, admin, empresa)")
def get_profile(
    profile_id: str, container: ContainerDep, principal: PrincipalDep
) -> dict[str, Any]:
    return container.profiles.get_profile(principal, profile_id)
