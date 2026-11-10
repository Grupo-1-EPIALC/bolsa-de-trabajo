"""Constructores de datos ficticios para los tests."""

from app.domain.models import (
    AcademicStatus,
    EducationItem,
    ExperienceRequirement,
    HoursRange,
    JobOpportunity,
    LanguageItem,
    Location,
    RequirementKind,
    SalaryRange,
    SkillItem,
    StudentProfile,
    WorkConditions,
)
from app.domain.normalization import normalize_text


def skill(name: str, level: int = 3, kind: str = "required") -> SkillItem:
    return SkillItem(
        name=name, normalized=normalize_text(name), level=level, kind=RequirementKind(kind)
    )


def lang(name: str, level: str, kind: str = "required") -> LanguageItem:
    return LanguageItem(
        name=name, normalized=normalize_text(name), level=level, kind=RequirementKind(kind)
    )


CABA = Location(country="AR", province="CABA", city="Buenos Aires", lat=-34.6037, lon=-58.3816)


def profile(**overrides: object) -> StudentProfile:
    base: dict[str, object] = {
        "id": "stu-test",
        "location": CABA,
        "skills": (skill("Python", 4), skill("SQL", 3), skill("Git", 4)),
        "languages": (lang("Inglés", "B2"),),
        "education": (EducationItem(level="university", status="in_progress"),),
        "years_experience": 1.0,
        "experience_skills": frozenset({"python", "sql", "docker"}),
        "academic": AcademicStatus(
            career="Ingeniería en Sistemas",
            current_year=4,
            progress_percent=70,
            student_shift=frozenset({"evening"}),
        ),
        "work_conditions": WorkConditions(
            work_schedule=frozenset({"part_time", "full_time"}),
            work_modality=frozenset({"hybrid", "remote"}),
            hybrid_onsite_days=3,
            employment_type=frozenset({"employee", "internship"}),
            weekly_hours=HoursRange(20, 40),
            shifts=frozenset({"morning", "afternoon"}),
            availability_start="immediate",
            max_commute_km=30,
            salary=SalaryRange(min=700000, max=900000, currency="ARS"),
        ),
    }
    base.update(overrides)
    return StudentProfile(**base)  # type: ignore[arg-type]


def job(**overrides: object) -> JobOpportunity:
    base: dict[str, object] = {
        "id": "job-test",
        "title": "Backend Python Jr.",
        "location": Location(
            country="AR", province="CABA", city="Buenos Aires", lat=-34.5997, lon=-58.3819
        ),
        "skills": (
            skill("Python", 3, "required"),
            skill("SQL", 3, "required"),
            skill("Docker", 3, "desired"),
        ),
        "languages": (lang("Inglés", "B1"),),
        "education": (EducationItem(level="university", status="in_progress"),),
        "experience": ExperienceRequirement(min_years=1),
        "work_conditions": WorkConditions(
            work_schedule=frozenset({"full_time"}),
            work_modality=frozenset({"hybrid"}),
            hybrid_onsite_days=2,
            employment_type=frozenset({"employee"}),
            weekly_hours=HoursRange(30, 40),
            shifts=frozenset({"morning"}),
            availability_start="within_15_days",
            salary=SalaryRange(min=800000, max=1000000, currency="ARS"),
        ),
    }
    base.update(overrides)
    return JobOpportunity(**base)  # type: ignore[arg-type]
