"""Dependencias de FastAPI: contenedor, identidad y paginación."""

import hmac
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, Query

from app.domain.auth import SERVICE_PRINCIPAL, Principal
from app.domain.errors import UnauthorizedError
from app.infrastructure.config import JobsSettings
from app.infrastructure.container import Container, build_container


@lru_cache
def get_container() -> Container:
    return build_container(JobsSettings.from_env())


def get_principal(
    container: Annotated[Container, Depends(get_container)],
    x_service_token: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    """Identifica a quien llama.

    - `X-Service-Token`: matching-service / mcp-tools / n8n por la red interna.
    - `Authorization: Bearer <JWT>`: usuarios del frontend, validado con el JWKS de auth-service.
    """
    if x_service_token is not None:
        expected = container.settings.service_token
        if expected and hmac.compare_digest(x_service_token, expected):
            return SERVICE_PRINCIPAL
        raise UnauthorizedError("Token de servicio inválido")
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        if token:
            return container.tokens.verify(token)
    raise UnauthorizedError("Falta el token de acceso (Authorization: Bearer <JWT>)")


@dataclass(frozen=True)
class Pagination:
    page: int
    size: int


def pagination(
    page: Annotated[int, Query(ge=1, le=1_000_000)] = 1,
    size: Annotated[int, Query(ge=1, le=200)] = 5,
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
) -> Pagination:
    """`limit` es el alias que usan matching-service y mcp-tools; gana sobre `size`.

    `page` acota el offset a ~200 millones de filas: evita pedidos con offsets de
    bigint que hicieron fallar la paginación en PostgreSQL.
    """
    return Pagination(page=page, size=limit if limit is not None else size)


ContainerDep = Annotated[Container, Depends(get_container)]
PrincipalDep = Annotated[Principal, Depends(get_principal)]
PaginationDep = Annotated[Pagination, Depends(pagination)]
