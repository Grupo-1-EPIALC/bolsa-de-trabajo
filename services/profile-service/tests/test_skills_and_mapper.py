"""UT-PROF-01 (SkillExtractor) y UT-PROF-02 (sugerencias del CV → borrador de perfil)."""

import json
from pathlib import Path

import pytest

from app.application.suggestion_mapper import (
    CvSuggestionMapper,
    guess_education_level,
    link_type,
    normalize_period,
    parse_education_status,
    parse_language_level,
    parse_location,
)
from app.domain.models import MANUAL_COMPLETION_INDICATOR as TODO
from app.domain.skills import SkillExtractor, normalize_text
from app.infrastructure.catalog import load_skill_catalog
from app.infrastructure.config import ProfileSettings
from tests.fakes import CV_SUGGESTIONS


@pytest.fixture(scope="module")
def extractor() -> SkillExtractor:
    return SkillExtractor(load_skill_catalog(ProfileSettings().skills_catalog_path))


# ------------------------------------------------------------------ UT-PROF-01 ---


def test_ut_prof_01_normaliza_sinonimos_y_acentos(extractor: SkillExtractor) -> None:
    assert extractor.normalize("Python3") == "python"
    assert extractor.normalize("Postgres") == "postgresql"
    assert extractor.normalize("  ReactJS ") == "react"
    assert extractor.normalize("Node") == "node.js"
    assert extractor.normalize("Resolución de Problemas") == "resolucion de problemas"
    assert extractor.normalize("Skill Desconocida") == "skill desconocida"
    assert normalize_text("  Comunicación   Efectiva ") == "comunicacion efectiva"


def test_ut_prof_01_label_y_categoria(extractor: SkillExtractor) -> None:
    assert extractor.label("postgres") == "PostgreSQL"
    assert extractor.label("algo raro ") == "algo raro"
    assert extractor.category("git").value == "tool"
    assert extractor.category("inventada") is None


def test_ut_prof_01_extrae_skills_del_texto(extractor: SkillExtractor) -> None:
    text = "Armé APIs REST con FastAPI y Postgres; deploy con Docker y k8s. React Native y C#."
    found = extractor.extract(text)
    assert found[:4] == ["rest", "fastapi", "postgresql", "docker"]
    assert "kubernetes" in found and "react native" in found and "c#" in found
    assert "react" not in found  # "react native" gana sobre "react"
    assert extractor.extract("") == []


def test_catalogo_usa_las_claves_de_matching() -> None:
    data = json.loads(Path(ProfileSettings().skills_catalog_path).read_text(encoding="utf-8"))
    keys = {item["key"] for item in data["skills"]}
    assert {"python", "node.js", "postgresql", "c#", "sql server", "scrum", "testing"} <= keys


# ------------------------------------------------------------------ UT-PROF-02 ---


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "San Isidro, Buenos Aires, Argentina",
            {"country": "AR", "province": "Buenos Aires", "city": "San Isidro"},
        ),
        (
            "Ciudad Autónoma de Buenos Aires",
            {"country": "AR", "province": "CABA", "city": "Buenos Aires"},
        ),
        ("Córdoba, Córdoba", {"country": "AR", "province": "Córdoba", "city": "Córdoba"}),
        ("Montevideo, Uruguay", {"country": "UY", "province": TODO, "city": "Montevideo"}),
        (TODO, {"country": TODO, "province": TODO, "city": TODO}),
        (
            {"country": "AR", "province": "Salta", "city": ""},
            {"country": "AR", "province": "Salta", "city": TODO},
        ),
    ],
)
def test_ut_prof_02_parsea_ubicacion(raw: object, expected: dict[str, str]) -> None:
    assert parse_location(raw) == expected


@pytest.mark.parametrize(
    ("raw", "level"),
    [
        ("Nativo", "native"),
        ("Intermedio B2", "B2"),
        ("c1", "C1"),
        ("Avanzado", "C1"),
        ("intermedio", "B1"),
        ("Básico", "A2"),
        ("bilingüe", "C2"),
        ("???", TODO),
    ],
)
def test_ut_prof_02_niveles_de_idioma(raw: str, level: str) -> None:
    assert parse_language_level(raw) == level


def test_ut_prof_02_educacion_periodos_y_links() -> None:
    assert parse_education_status("En curso") == "in_progress"
    assert parse_education_status("Incompleto") == "incomplete"
    assert parse_education_status("Recibido") == "completed"
    assert parse_education_status(TODO) == TODO
    assert guess_education_level("Ingeniería en Sistemas", "UTN") == "university"
    assert guess_education_level("Tecnicatura en Programación", "") == "tertiary"
    assert guess_education_level("Bachiller", "Colegio Nacional") == "secondary"
    assert guess_education_level("Maestría en Datos", "") == "postgraduate"
    assert guess_education_level("Otra cosa", "") == TODO
    assert normalize_period("03/2024") == "2024-03"
    assert normalize_period("2023") == "2023"
    assert normalize_period("2021-7") == "2021-07"
    assert normalize_period("Presente", end=True) == "actual"
    assert normalize_period(TODO, end=True) == "actual"
    assert normalize_period("sin fecha") == TODO
    assert link_type("https://www.linkedin.com/in/x") == "linkedin"
    assert link_type("https://gitlab.com/x") == "github"
    assert link_type("https://mi.vercel.app") == "portfolio"
    assert link_type("https://ejemplo.com") == "other"


def test_ut_prof_02_borrador_con_campos_a_completar(extractor: SkillExtractor) -> None:
    mapped = CvSuggestionMapper(extractor).to_profile_draft(
        CV_SUGGESTIONS, account_email="cuenta@example.com"
    )
    draft = mapped["profile_draft"]
    assert "null" not in json.dumps(draft)  # nunca null (AGENTS.md §5.3)
    assert draft["personal"]["email"] == "cuenta@example.com"  # precargado desde la cuenta
    assert draft["personal"]["location"] == {
        "country": "AR",
        "province": "Buenos Aires",
        "city": "San Isidro",
    }
    skills = {s["normalized"]: s for s in draft["skills"]}
    assert skills["python"]["name"] == "Python" and skills["python"]["level"] == 4
    assert skills["docker"]["level"] == TODO
    assert {"postgresql", "git", "rest", "pytest"} <= set(skills)  # mencionadas en el texto
    assert all(s["source"] == "cv_ai" and s["confirmed"] is False for s in draft["skills"])
    exp = draft["experience"][0]
    assert exp["start"] == "2024-03" and exp["end"] == "actual"
    assert "FastAPI" in exp["skills_used"]
    edu = draft["education"][0]
    assert edu["level"] == "university" and edu["status"] == "in_progress"
    assert "start" not in edu  # opcional y desconocido: se omite
    assert draft["academic_status"]["career"] == "Ingeniería en Sistemas de Información"
    assert draft["languages"][0] == {"name": "Inglés", "normalized": "ingles", "level": "B2"}
    assert draft["links"] == [{"type": "github", "url": "https://github.com/lucia-ficticia"}]
    assert draft["certifications"] == [{"name": "Curso de Docker Ficticio"}]
    review = set(mapped["review_fields"])
    assert {"headline", "personal.phone"} <= review
    assert any(path.startswith("skills[") and path.endswith(".level") for path in review)


def test_ut_prof_02_headline_del_cv_se_precarga_sin_revision(extractor: SkillExtractor) -> None:
    mapped = CvSuggestionMapper(extractor).to_profile_draft(
        {"headline": "Estudiante de Contador Público · Facturación", "headline_source": "cv"}
    )
    assert mapped["profile_draft"]["headline"] == "Estudiante de Contador Público · Facturación"
    assert "headline" not in mapped["review_fields"]
    assert mapped["suggested_fields"] == []


def test_ut_prof_02_headline_sugerido_se_marca_para_revisar(extractor: SkillExtractor) -> None:
    mapped = CvSuggestionMapper(extractor).to_profile_draft(
        {"headline": "Profesorado de Primaria · " + "x" * 200, "headline_source": "suggested"}
    )
    headline = mapped["profile_draft"]["headline"]
    assert headline.startswith("Profesorado de Primaria") and len(headline) <= 140
    assert mapped["suggested_fields"] == ["headline"]
    assert "headline" not in mapped["review_fields"]  # tiene valor: se revisa, no se completa


def test_ut_prof_02_headline_sin_dato_queda_para_completar(extractor: SkillExtractor) -> None:
    for value in (None, "", TODO):
        mapped = CvSuggestionMapper(extractor).to_profile_draft(
            {"headline": value, "headline_source": "suggested"}
        )
        assert mapped["profile_draft"]["headline"] == TODO
        assert "headline" in mapped["review_fields"]
        assert mapped["suggested_fields"] == []


def test_ut_prof_02_cv_vacio_no_inventa(extractor: SkillExtractor) -> None:
    mapped = CvSuggestionMapper(extractor).to_profile_draft({})
    draft = mapped["profile_draft"]
    assert draft["skills"] == [] and draft["experience"] == [] and draft["languages"] == []
    assert draft["personal"]["name"] == TODO and draft["personal"]["email"] == TODO
    assert "academic_status" not in draft
