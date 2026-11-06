"""Verificación del JWT RS256 emitido por auth-service."""

import pytest

from app.domain.auth import Role
from app.domain.errors import UnauthorizedError
from tests.jwt_helpers import STUDENT_001, make_token, verifier


def test_verifier_accepts_auth_service_token() -> None:
    principal = verifier().verify(make_token(STUDENT_001, "student"))
    assert principal.subject == STUDENT_001
    assert principal.role is Role.STUDENT
    assert principal.access_token is not None


@pytest.mark.parametrize(
    "claims",
    [
        {"exp": 1},
        {"aud": "otra-api"},
        {"iss": "otro-emisor"},
        {"role": "superuser"},
        {"role": "service"},
    ],
)
def test_verifier_rejects_invalid_claims(claims: dict[str, object]) -> None:
    with pytest.raises(UnauthorizedError):
        verifier().verify(make_token(STUDENT_001, "student", extra=claims))


def test_verifier_rejects_wrong_signature_and_garbage() -> None:
    with pytest.raises(UnauthorizedError):
        verifier().verify(make_token(STUDENT_001, "student", other_key=True))
    with pytest.raises(UnauthorizedError):
        verifier().verify("no-es-un-jwt")
