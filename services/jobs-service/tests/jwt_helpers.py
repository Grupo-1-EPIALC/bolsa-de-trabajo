"""JWT de prueba con la misma forma que emite auth-service (RS256, `{sub, role}`, iss/aud, kid)."""

import time
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from app.infrastructure.jwt_verifier import JwtTokenVerifier

ISSUER = "bolsa-auth"
AUDIENCE = "bolsa-api"
KID = "bolsa-auth-1"

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)

COMPANY_001 = "22222222-2222-4222-8222-000000000001"
COMPANY_002 = "22222222-2222-4222-8222-000000000002"
STUDENT_001 = "11111111-1111-4111-8111-000000000001"
ADMIN_001 = "33333333-3333-4333-8333-000000000001"


class StaticKeyResolver:
    def key_for(self, token: str) -> Any:
        return _PRIVATE_KEY.public_key()


def verifier() -> JwtTokenVerifier:
    return JwtTokenVerifier(StaticKeyResolver(), ISSUER, AUDIENCE)


def make_token(
    sub: str, role: str, *, other_key: bool = False, extra: dict[str, Any] | None = None
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": sub,
        "role": role,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + 900,
    }
    payload.update(extra or {})
    key = _OTHER_KEY if other_key else _PRIVATE_KEY
    return jwt.encode(payload, key, algorithm="RS256", headers={"kid": KID})


def bearer(sub: str, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(sub, role)}"}
