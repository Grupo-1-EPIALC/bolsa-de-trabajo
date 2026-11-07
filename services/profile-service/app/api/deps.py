"""Dependencias de FastAPI: contenedor e identidad de quien llama."""

import hmac
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header

from app.domain.auth import SERVICE_PRINCIPAL, Principal
from app.domain.errors import AccountDeletedError, UnauthorizedError
from app.infrastructure.config import ProfileSettings
from app.infrastructure.container import Container, build_container


@lru_cache
def get_container() -> Container:
    return build_container(ProfileSettings.from_env())


def get_principal(
    container: Annotated[Container, Depends(get_container)],
    x_service_token: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    """Identifica a quien llama.

    - `X-Service-Token`: matching-service / mcp-tools / n8n por la red interna (el gateway lo
      borra en las peticiones externas). Nunca se acepta como Bearer.
    - `Authorization: Bearer <JWT>`: usuarios, validado localmente con el JWKS de auth-service.
      El JWT de una cuenta dada de baja sigue siendo válido hasta que vence (15 min): se
      rechaza con `401 ACCOUNT_DELETED` (lo avisa auth-service con `account.deleted`).
    """
    if x_service_token is not None:
        expected = container.settings.service_token
        if expected and hmac.compare_digest(x_service_token, expected):
            return SERVICE_PRINCIPAL
        raise UnauthorizedError("Token de servicio inválido")
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        if token:
            principal = container.tokens.verify(token)
            if container.deleted_accounts.contains(principal.subject):
                raise AccountDeletedError()
            return principal
    raise UnauthorizedError("Falta el token de acceso (Authorization: Bearer <JWT>)")


ContainerDep = Annotated[Container, Depends(get_container)]
PrincipalDep = Annotated[Principal, Depends(get_principal)]
