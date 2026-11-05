"""Validación local del JWT de auth-service (RS256) con la clave pública del JWKS.

auth-service firma `{sub, role}` con `iss=JWT_ISSUER`, `aud=JWT_AUDIENCE`, `kid` en el header y
publica las claves en `/api/v1/auth/.well-known/jwks.json` (AGENTS.md §4.1).
"""

from typing import Any, Protocol

import jwt

from app.domain.auth import USER_ROLES, Principal, Role
from app.domain.errors import UnauthorizedError


class SigningKeyResolver(Protocol):
    def key_for(self, token: str) -> Any: ...


class JwksKeyResolver:
    """Busca la clave por `kid` en el JWKS (con caché; se refresca si aparece un `kid` nuevo)."""

    def __init__(self, jwks_url: str, timeout_seconds: int = 5) -> None:
        if not jwks_url.startswith(("http://", "https://")):
            raise ValueError(f"JWKS_URL inválida: {jwks_url!r}")
        self._client = jwt.PyJWKClient(
            jwks_url, cache_keys=True, lifespan=600, timeout=timeout_seconds
        )

    def key_for(self, token: str) -> Any:
        try:
            return self._client.get_signing_key_from_jwt(token).key
        except jwt.PyJWKClientConnectionError as exc:
            raise UnauthorizedError("No se pudo obtener el JWKS de auth-service") from exc
        except jwt.PyJWKClientError as exc:
            raise UnauthorizedError("JWT firmado con una clave desconocida") from exc


class JwtTokenVerifier:
    def __init__(self, keys: SigningKeyResolver, issuer: str, audience: str) -> None:
        self._keys = keys
        self._issuer = issuer
        self._audience = audience

    def verify(self, token: str) -> Principal:
        try:
            key = self._keys.key_for(token)
            claims: dict[str, Any] = jwt.decode(
                token,
                key=key,
                algorithms=["RS256"],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["exp", "sub", "iss", "aud"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise UnauthorizedError("El token expiró") from exc
        except jwt.PyJWTError as exc:
            raise UnauthorizedError("Token inválido", {"reason": type(exc).__name__}) from exc
        role = str(claims.get("role", ""))
        if role not in {r.value for r in USER_ROLES}:
            raise UnauthorizedError("El token no tiene un rol válido")
        return Principal(subject=str(claims["sub"]), role=Role(role))
