"""UT-PROF-04 (casos de uso del perfil) y UT-PROF-05 (vistas por rol y pool para matching)."""

import copy
from typing import Any

import pytest

from app.domain.auth import SERVICE_PRINCIPAL, Principal, Role
from app.domain.errors import (
    ForbiddenError,
    InvalidInputError,
    ProfileAlreadyExistsError,
    ProfileIncompleteError,
    ProfileNotFoundError,
    SuggestionsNotFoundError,
    UnsupportedFormatError,
)
from app.infrastructure.container import Container
from tests.conftest import COMPLETE_PROFILE, wait_job
from tests.fakes import RecordingPublisher

MD_CV = b"# Lucia Ficticia\nPython y FastAPI"


def _complete(container: Container, student: Principal) -> dict[str, Any]:
    return container.profiles.create_mine(student, copy.deepcopy(COMPLETE_PROFILE))


# ------------------------------------------------------------------ UT-PROF-04 ---


def test_ut_prof_04_sin_perfil_da_404_y_solo_estudiantes(
    container: Container, student: Principal
) -> None:
    with pytest.raises(ProfileNotFoundError):
        container.profiles.get_mine(student)
    company = Principal(subject="c1", role=Role.COMPANY)
    with pytest.raises(ForbiddenError):
        container.profiles.create_mine(company)
    with pytest.raises(ForbiddenError):
        container.profiles.get_mine(SERVICE_PRINCIPAL)


def test_ut_prof_04_alta_manual_precarga_email_y_queda_borrador(
    container: Container, student: Principal, publisher: RecordingPublisher
) -> None:
    body = container.profiles.create_mine(student)
    assert body["id"] == "prof-test-001" and body["user_id"] == student.subject
    assert body["personal"]["email"] == "cuenta@example.com"
    assert body["status"] == "draft" and body["completion"]["origin"] == "RULES"
    assert body["has_cv_suggestions"] is False
    assert len(publisher.events) == 1
    with pytest.raises(ProfileAlreadyExistsError):
        container.profiles.create_mine(student)


def test_ut_prof_04_completar_perfil_normaliza_y_versiona(
    container: Container, student: Principal, publisher: RecordingPublisher
) -> None:
    container.profiles.create_mine(student)
    body = container.profiles.update_mine(student, copy.deepcopy(COMPLETE_PROFILE))
    assert body["status"] == "complete" and body["version"] == 2
    assert body["completion"]["can_generate_cv"] is True
    skills = {s["normalized"]: s for s in body["skills"]}
    assert skills["python"]["category"] == "hard"
    assert skills["git"]["category"] == "tool"
    assert "postgresql" in skills
    assert body["experience"][0]["months"] == 21  # 2025-03 → 2026-11 (reloj fijo)
    assert body["languages"][0]["normalized"] == "ingles"
    assert body["consents"]["accepted_at"] == "2026-11-05T12:00:00+00:00"
    assert publisher.events[-1].status.value == "complete"


@pytest.mark.parametrize(
    ("changes", "fragment"),
    [
        ({"summary": "COMPLETAR_MANUALMENTE"}, "sin completar"),
        ({"status": "complete"}, "no editables"),
        ({"skills": [{"name": "Python", "level": 9}]}, "inconsistentes"),
        ({"work_conditions": {"weekly_hours": {"min": 30, "max": 10}}}, "inconsistentes"),
        (
            {"work_conditions": {"salary": {"min": 10, "max": 5, "currency": "ARS"}}},
            "inconsistentes",
        ),
        ({"work_conditions": {"salary": {"min": 10}}}, "inconsistentes"),
        ({"visibility": "todos"}, "inválido"),
    ],
)
def test_ut_prof_04_rechaza_datos_invalidos(
    container: Container, student: Principal, changes: dict[str, Any], fragment: str
) -> None:
    container.profiles.create_mine(student)
    with pytest.raises(InvalidInputError) as exc:
        container.profiles.update_mine(student, changes)
    assert fragment in exc.value.message or fragment in str(exc.value.details)


def test_ut_prof_04_skills_duplicadas_se_unifican(container: Container, student: Principal) -> None:
    container.profiles.create_mine(student)
    body = container.profiles.update_mine(
        student, {"skills": [{"name": "Python", "level": 4}, {"name": "py", "level": 2}]}
    )
    assert [s["level"] for s in body["skills"]] == [4]


def test_ut_prof_04_cv_crea_borrador_y_guarda_sugerencias(
    container: Container, student: Principal
) -> None:
    snapshot = container.profiles.start_cv_extraction(
        student, filename="cv.md", content=MD_CV, mime_type="text/markdown"
    )
    assert snapshot["profile_id"] == "prof-test-001"
    done = wait_job(lambda j: container.profiles.get_cv_job(student, j), snapshot["job_id"])
    assert done["status"] == "completed"
    result = done["result"]
    assert result["origin"] == "AI" and "disclaimer" in result
    assert result["profile_draft"]["personal"]["name"] == "Lucía Fernández"
    assert "personal.phone" in result["review_fields"]

    me = container.profiles.get_mine(student)
    assert me["has_cv_suggestions"] is True
    assert me["cv_files"][0]["original_filename"] == "cv.md"
    assert me["skills"] == [] or "skills" not in me  # nada se confirmó todavía
    stored = container.profiles.get_suggestions(student)
    assert stored["profile_draft"] == result["profile_draft"]

    container.profiles.discard_suggestions(student)
    with pytest.raises(SuggestionsNotFoundError):
        container.profiles.get_suggestions(student)
    with pytest.raises(SuggestionsNotFoundError):
        container.profiles.discard_suggestions(student)


def test_ut_prof_04_job_ajeno_da_404(container: Container, student: Principal) -> None:
    snapshot = container.profiles.start_cv_extraction(
        student, filename="cv.md", content=MD_CV, mime_type="text/markdown"
    )
    other = Principal(subject="otro-estudiante", role=Role.STUDENT)
    container.profiles.create_mine(other)
    with pytest.raises(ProfileNotFoundError):
        container.profiles.get_cv_job(other, snapshot["job_id"])


def test_ut_prof_04_generar_cv_exige_datos_y_formato(
    container: Container, student: Principal
) -> None:
    container.profiles.create_mine(student)
    with pytest.raises(ProfileIncompleteError) as exc:
        container.profiles.generate_cv(student, "docx")
    fields = {m["field"] for m in exc.value.details["missing"]}
    assert {"personal.name", "skills"} <= fields
    with pytest.raises(UnsupportedFormatError):
        container.profiles.generate_cv(student, "odt")
    container.profiles.update_mine(student, copy.deepcopy(COMPLETE_PROFILE))
    generated = container.profiles.generate_cv(student, "docx")
    assert generated.filename == "CV_Lucia_Fernandez.docx"
    assert generated.file.content[:2] == b"PK"


def test_ut_prof_04_evento_y_cuenta_son_best_effort(
    container: Container, student: Principal
) -> None:
    from tests.fakes import FakeAccounts

    container.profiles._publisher = RecordingPublisher(fail=True)  # type: ignore[attr-defined]
    container.profiles._accounts = FakeAccounts(fail=True)  # type: ignore[attr-defined]
    body = container.profiles.create_mine(student)
    assert body["personal"]["email"] == ""


# ------------------------------------------------------------------ UT-PROF-05 ---


def test_ut_prof_05_vistas_minimizan_datos(container: Container, student: Principal) -> None:
    profile_id = _complete(container, student)["id"]
    service = container.profiles.get_profile(SERVICE_PRINCIPAL, profile_id)
    assert "inclusion" not in service and "consents" not in service
    assert "phone" not in service["personal"] and "birth_year" not in service["personal"]
    assert service["personal"]["email"] == "lucia.ficticia@example.com"
    assert service["work_conditions"]["salary"]["min"] == 600000  # matching aplica visibility
    assert service["years_experience"] == 1.75

    company = container.profiles.get_profile(Principal("c1", Role.COMPANY), profile_id)
    assert "email" not in company["personal"]
    assert "salary" not in company["work_conditions"]  # visibility on_match

    admin = container.profiles.get_profile(Principal("a1", Role.ADMIN), profile_id)
    assert "inclusion" not in admin and admin["completion"]["status"] == "complete"

    owner = container.profiles.get_profile(student, profile_id)
    assert owner["inclusion"]["disability_certificate"] is True

    with pytest.raises(ProfileNotFoundError):
        container.profiles.get_profile(Principal("otro", Role.STUDENT), profile_id)
    with pytest.raises(ProfileNotFoundError):
        container.profiles.get_profile(SERVICE_PRINCIPAL, "no-existe")


def test_ut_prof_05_empresa_no_ve_perfiles_ocultos(
    container: Container, student: Principal
) -> None:
    profile_id = _complete(container, student)["id"]
    container.profiles.update_mine(student, {"visibility": "hidden"})
    with pytest.raises(ProfileNotFoundError):
        container.profiles.get_profile(Principal("c1", Role.COMPANY), profile_id)


def test_ut_prof_05_pool_para_matching(seeded: Container) -> None:
    pool = seeded.profiles.list_profiles(SERVICE_PRINCIPAL, limit=200)
    assert pool["total"] == 15 and len(pool["items"]) == 15
    first = pool["items"][0]
    assert first["id"] == "stu-001" and first["status"] == "complete"
    assert "phone" not in first["personal"]

    python = seeded.profiles.list_profiles(SERVICE_PRINCIPAL, skills=["Python3"], limit=200)
    assert 0 < python["total"] < 15
    assert all(any(s["normalized"] == "python" for s in p["skills"]) for p in python["items"])

    page = seeded.profiles.list_profiles(SERVICE_PRINCIPAL, limit=4, page=2)
    assert [p["id"] for p in page["items"]] == ["stu-005", "stu-006", "stu-007", "stu-008"]
    assert page["pages"] == 4

    admin = seeded.profiles.list_profiles(Principal("a1", Role.ADMIN), limit=1)
    assert "completion" in admin["items"][0]
    with pytest.raises(ForbiddenError):
        seeded.profiles.list_profiles(Principal("c1", Role.COMPANY))


def test_ut_prof_05_pool_excluye_borradores_y_no_buscando(
    container: Container, student: Principal
) -> None:
    _complete(container, student)
    draft_student = Principal(subject="u-draft", role=Role.STUDENT)
    container.profiles.create_mine(draft_student)
    assert container.profiles.list_profiles(SERVICE_PRINCIPAL)["total"] == 1
    container.profiles.update_mine(student, {"job_search_status": "not_looking"})
    assert container.profiles.list_profiles(SERVICE_PRINCIPAL)["total"] == 0
    assert container.profiles.list_profiles(SERVICE_PRINCIPAL, include_all=True)["total"] == 2


def test_seed_es_idempotente(seeded: Container) -> None:
    from app.infrastructure.seed import seed_profiles

    assert seed_profiles(seeded.profiles, seeded.settings.seed_path) == 0
    assert seed_profiles(seeded.profiles, "/no/existe.json") == 0
