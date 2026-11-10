"""UT-MATCH-09: normalización de skills, mapeo del contrato (y legacy) y carga de reglas."""

from datetime import date
from pathlib import Path

import pytest

from app.application.mappers import (
    JobMapper,
    ProfileMapper,
    map_location,
    parse_legacy_education,
    years_from_experience,
)
from app.domain.errors import InvalidRulesError
from app.domain.models import RequirementKind
from app.domain.normalization import SkillNormalizer, is_missing, normalize_text
from app.domain.rules import ScoringRules
from app.infrastructure.config import DATA_DIR
from app.infrastructure.rules_loader import load_rules, load_synonyms, rules_from_mapping

NORMALIZER = SkillNormalizer({"ReactJS": "React", "postgres": "PostgreSQL"})


def test_ut_match_09_skill_normalization_accents_and_synonyms() -> None:
    assert normalize_text("  Diseño   UX ") == "diseno ux"
    assert NORMALIZER.normalize("reactjs") == "react"
    assert NORMALIZER.normalize("Postgres") == "postgresql"
    assert NORMALIZER.normalize("Python") == "python"


def test_is_missing_placeholder() -> None:
    assert is_missing("COMPLETAR_MANUALMENTE")
    assert is_missing("  ")
    assert is_missing(None)
    assert not is_missing("CABA")


def test_profile_mapper_contract_structure() -> None:
    data = {
        "id": "stu-x",
        "personal": {"name": "Ana Ficticia", "location": {"country": "AR", "city": "Rosario"}},
        "skills": [{"name": "ReactJS", "level": 4}, {"name": "COMPLETAR_MANUALMENTE"}],
        "languages": [{"name": "Inglés", "level": "B2"}],
        "experience": [{"start": "2024-01", "end": "2025-01"}],
        "work_conditions": {
            "work_modality": ["remote"],
            "weekly_hours": {"min": 20},
            "salary": {"min": 500000, "currency": "ars"},
            "work_authorization": ["ar"],
        },
        "academic_status": {"career": "Sistemas", "student_shift": ["evening"]},
    }
    profile = ProfileMapper(NORMALIZER).to_domain(data)

    assert profile.display_name == "Ana Ficticia"
    assert profile.location.city == "Rosario"
    assert [s.normalized for s in profile.skills] == ["react"]
    assert profile.years_experience == 1.0
    wc = profile.work_conditions
    assert wc.work_modality == frozenset({"remote"})
    assert wc.weekly_hours is not None and wc.weekly_hours.max == 20
    assert wc.salary is not None and wc.salary.currency == "ARS"
    assert wc.work_authorization == frozenset({"AR"})
    assert profile.academic.student_shift == frozenset({"evening"})


def test_profile_mapper_legacy_mock_shape() -> None:
    data = {
        "id": "stu-001",
        "full_name": "Valentina Gómez",
        "years_experience": 2,
        "education_level": "universitario_en_curso",
        "skills": [{"name": "Python", "level": "avanzado"}],
    }
    profile = ProfileMapper(NORMALIZER).to_domain(data)

    assert profile.display_name == "Valentina Gómez"
    assert profile.years_experience == 2
    assert profile.skills[0].level == 4
    assert profile.education[0].level == "university"
    assert profile.education[0].status == "in_progress"


def test_job_mapper_contract_and_legacy() -> None:
    mapper = JobMapper(NORMALIZER)
    contract = mapper.to_domain(
        {
            "id": "job-x",
            "company_snapshot": {"name": "Empresa Ficticia"},
            "requirements": {
                "skills": [{"name": "Python", "level": 3, "kind": "excluding"}],
                "experience": {"min_years": 2},
                "academic": {"min_progress_percent": 50, "careers": ["Sistemas"]},
            },
        }
    )
    legacy = mapper.to_domain(
        {
            "id": "job-001",
            "company_name": "PampaTech S.A.",
            "min_years_experience": 1,
            "requirements": [{"skill": "FastAPI", "level": 3, "kind": "desired"}],
            "languages": [{"name": "Inglés", "level": "B1"}],
        }
    )

    assert contract.company_name == "Empresa Ficticia"
    assert contract.skills[0].kind is RequirementKind.EXCLUDING
    assert contract.experience.min_years == 2
    assert contract.academic.careers == ("Sistemas",)
    assert legacy.skills[0].name == "FastAPI"
    assert legacy.skills[0].kind is RequirementKind.DESIRED
    assert legacy.experience.min_years == 1
    assert legacy.languages[0].level == "B1"


def test_location_from_free_text() -> None:
    loc = map_location("San Isidro, Buenos Aires, AR")
    assert (loc.city, loc.province, loc.country) == ("San Isidro", "Buenos Aires", "AR")
    assert map_location("COMPLETAR_MANUALMENTE").is_empty


@pytest.mark.parametrize(
    ("text", "level", "status"),
    [
        ("terciario_completo", "tertiary", "completed"),
        ("universitario_incompleto", "university", "incomplete"),
        ("posgrado en curso", "postgraduate", "in_progress"),
    ],
)
def test_parse_legacy_education(text: str, level: str, status: str) -> None:
    parsed = parse_legacy_education(text)
    assert parsed is not None
    assert (parsed.level, parsed.status) == (level, status)


def test_years_from_experience_ongoing_and_months() -> None:
    today = date(2026, 1, 1)
    items = [{"start": "2025-01", "end": "actual"}, {"months": 6}, {"start": "bad"}]
    assert years_from_experience(items, today) == 1.5


def test_default_rules_file_loads_and_weights_sum_100() -> None:
    rules = load_rules(DATA_DIR / "scoring_rules.yaml")
    assert sum(rules.weights.values()) == 100
    assert rules.excluding_cap == 40
    assert rules.version == "2.0.0"
    assert rules.weight("experience") == 25 and rules.weight("conditions") == 7
    assert not rules.condition("work_modality").hard
    assert not rules.condition("work_schedule").hard
    assert rules.condition("driver_license").hard
    assert not rules.condition("salary").hard
    assert rules.training.similar_jobs == 10 and rules.training.max_gaps == 8
    assert rules.experience.reference_years == 1
    assert load_synonyms(DATA_DIR / "skill_synonyms.json")["reactjs"] == "react"


def test_invalid_rules_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(InvalidRulesError):
        rules_from_mapping({"weights": {"required_skills": 90}})
    with pytest.raises(InvalidRulesError):
        ScoringRules(excluding_cap=150)
    with pytest.raises(InvalidRulesError):
        rules_from_mapping({"experience": {"relevance_share": 2}})
    with pytest.raises(InvalidRulesError):
        rules_from_mapping({"training": {"similar_jobs": 0}})
    with pytest.raises(InvalidRulesError):
        load_rules(tmp_path / "no-existe.yaml")
    assert load_synonyms(tmp_path / "no-existe.json") == {}
