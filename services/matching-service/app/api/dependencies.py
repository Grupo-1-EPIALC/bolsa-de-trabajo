"""Dependencias de FastAPI: contenedor e identidad de quien llama."""

import hmac
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header

from app.application.access_policy import AccessPolicy
from app.domain.auth import SERVICE_PRINCIPAL, Principal
from app.domain.errors import UnauthorizedError
from app.infrastructure.config import MatchingSettings
from app.infrastructure.container import Container, build_container


@lru_cache
def get_container() -> Container:
    return build_container(MatchingSettings.from_env())


def get_principal(
    container: Annotated[Container, Depends(get_container)],
    x_service_token: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    """Identifica a quien llama.

    - `X-Service-Token`: n8n / mcp-tools por la red interna. El gateway borra este header en
      las peticiones externas, por eso es el único lugar donde se acepta el token interno.
    - `Authorization: Bearer <JWT>`: usuarios (frontend), validado con el JWKS de auth-service.
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


def require_service(principal: Annotated[Principal, Depends(get_principal)]) -> Principal:
    """Endpoints internos: sólo n8n / mcp-tools."""
    AccessPolicy.require_service(principal)
    return principal
