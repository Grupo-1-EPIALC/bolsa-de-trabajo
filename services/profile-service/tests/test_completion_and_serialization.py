"""UT-PROF-03: completitud del perfil por reglas · serialización dataclass ↔ JSON."""

from datetime import UTC, datetime

import pytest

from app.domain.completion import CompletionRule, ProfileCompletenessPolicy, Step
from app.domain.enums import (
    AvailabilityStart,
    EducationLevel,
    EducationStatus,
    EmploymentType,
    ProfileStatus,
    WorkModality,
    WorkSchedule,
)
from app.domain.profile import (
    Consents,
    Education,
    Location,
    PersonalInfo,
    Skill,
    StudentProfile,
    WorkPreferences,
)
from app.domain.serialization import DecodeError, drop_none, from_plain, to_plain

NOW = datetime(2026, 11, 5, tzinfo=UTC)


def _empty() -> StudentProfile:
    return StudentProfile(id="p1", user_id="u1", created_at=NOW, updated_at=NOW)


def _cv_ready() -> StudentProfile:
    return StudentProfile(
        id="p1",
        user_id="u1",
        created_at=NOW,
        updated_at=NOW,
        personal=PersonalInfo(
            name="Ana Ficticia",
            email="ana@example.com",
            location=Location(country="AR", province="CABA", city="Buenos Aires"),
        ),
        summary="Resumen ficticio",
        skills=(Skill(name="Python", level=3),),
        education=(
            Education(
                institution="UTN",
                degree="Sistemas",
                level=EducationLevel.UNIVERSITY,
                status=EducationStatus.IN_PROGRESS,
            ),
        ),
    )


def test_ut_prof_03_perfil_vacio_es_borrador() -> None:
    result = ProfileCompletenessPolicy().evaluate(_empty())
    assert result.status is ProfileStatus.DRAFT
    assert result.can_generate_cv is False
    assert result.percent == 0
    required = {m.field for m in result.missing if m.required}
    assert {
        "personal.name",
        "skills",
        "work_conditions.work_modality",
        "consents.data_processing",
    } <= required
    assert {s.step for s in result.steps if not s.complete} == {
        Step.CV,
        Step.PREFERENCES,
        Step.PRIVACY,
    }


def test_ut_prof_03_cv_listo_sin_preferencias_permite_generar_cv() -> None:
    result = ProfileCompletenessPolicy().evaluate(_cv_ready())
    assert result.can_generate_cv is True
    assert result.status is ProfileStatus.DRAFT
    cv_step = next(s for s in result.steps if s.step is Step.CV)
    assert cv_step.complete and cv_step.missing_recommended > 0


def test_ut_prof_03_perfil_completo() -> None:
    import dataclasses

    profile = dataclasses.replace(
        _cv_ready(),
        work_conditions=WorkPreferences(
            work_schedule=(WorkSchedule.PART_TIME,),
            work_modality=(WorkModality.REMOTE,),
            employment_type=(EmploymentType.INTERNSHIP,),
            availability_start=AvailabilityStart.IMMEDIATE,
        ),
        consents=Consents(data_processing=True),
    )
    result = ProfileCompletenessPolicy().evaluate(profile)
    assert result.status is ProfileStatus.COMPLETE
    assert 50 < result.percent < 100  # faltan recomendados
    assert all(not m.required for m in result.missing)


def test_ut_prof_03_reglas_extensibles() -> None:
    rule = CompletionRule("headline", Step.CV, "Falta", lambda p: bool(p.headline))
    result = ProfileCompletenessPolicy([rule]).evaluate(_empty())
    assert result.percent == 0 and result.missing[0].field == "headline"
    assert ProfileCompletenessPolicy([]).evaluate(_empty()).percent == 100


def test_serializacion_ida_y_vuelta() -> None:
    profile = _cv_ready()
    plain = to_plain(profile)
    assert plain["skills"][0]["source"] == "manual"
    assert plain["created_at"] == "2026-11-05T00:00:00+00:00"
    assert from_plain(StudentProfile, plain) == profile
    assert "phone" not in drop_none(plain)["personal"]


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        ({"skills": [{"name": "Python", "level": "alto"}]}, "entero"),
        ({"work_conditions": {"work_modality": ["teletrabajo"]}}, "permitidos"),
        ({"skills": "python"}, "lista"),
        ({"personal": "Ana"}, "objeto"),
        ({"education": [{"institution": "UTN"}]}, "faltan campos"),
        ({"references_available": "si"}, "true/false"),
        ({"summary": 5}, "texto"),
        ({"created_at": "ayer"}, "fecha"),
    ],
)
def test_serializacion_valida_tipos(patch: dict[str, object], message: str) -> None:
    plain = {**to_plain(_empty()), **patch}
    with pytest.raises(DecodeError, match=message):
        from_plain(StudentProfile, plain)
