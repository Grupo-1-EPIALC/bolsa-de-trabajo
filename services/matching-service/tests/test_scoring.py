"""UT-MATCH-01 a UT-MATCH-06: criterios de scoring, regla excluyente y skills faltantes."""

from dataclasses import replace

import pytest

from app.domain.criteria import (
    ConditionsCriterion,
    DesiredSkillsCriterion,
    EducationCriterion,
    ExperienceCriterion,
    LanguagesCriterion,
    LevelsCriterion,
    RequiredSkillsCriterion,
)
from app.domain.engine import MatchingEngine, build_engine
from app.domain.missing_skills import MissingSkillsAnalyzer
from app.domain.models import EducationItem, ExperienceRequirement, Priority, RequirementKind
from app.domain.rules import ScoringRules
from tests.builders import job, lang, profile, skill


def _engine() -> MatchingEngine:
    return build_engine(ScoringRules(), lambda: "2026-11-04T00:00:00Z")


def test_ut_match_01_perfect_match_scores_100() -> None:
    p = profile(skills=(skill("Python", 4), skill("SQL", 3), skill("Docker", 3)))
    result = _engine().match(p, job())

    assert result.score == 100
    assert not result.excluding_cap_applied
    assert {c.criterion for c in result.breakdown} == {
        "required_skills",
        "desired_skills",
        "levels",
        "experience",
        "education",
        "languages",
        "conditions",
    }
    assert sum(c.weight for c in result.breakdown) == 100


def test_technical_and_experience_weigh_more_than_conditions() -> None:
    weights = ScoringRules().weights
    technical = sum(weights[k] for k in ("required_skills", "desired_skills", "levels"))
    assert weights["experience"] > weights["conditions"]
    assert weights["experience"] > weights["desired_skills"]
    assert technical + weights["experience"] >= 80
    assert weights["conditions"] <= 10


def test_ut_match_02_required_skills_proportional() -> None:
    criterion = RequiredSkillsCriterion(50)
    p = profile(skills=(skill("Python", 4),))

    assert criterion.evaluate(p, job()).earned == 25.0


def test_ut_match_03_desired_skills_full_when_job_has_none() -> None:
    criterion = DesiredSkillsCriterion(15)
    j = job(skills=(skill("Python", 3),))

    assert criterion.evaluate(profile(skills=()), j).earned == 15.0
    assert criterion.evaluate(profile(skills=()), job()).earned == 0.0


def test_ut_match_04_levels_average_ratio() -> None:
    criterion = LevelsCriterion(15)
    p = profile(skills=(skill("Python", 3), skill("SQL", 1)))
    j = job(skills=(skill("Python", 3), skill("SQL", 2)))

    # (1.0 + 0.5) / 2 * 15
    assert criterion.evaluate(p, j).earned == 11.25
    assert criterion.evaluate(profile(skills=()), j).earned == 0.0


def test_ut_match_05_excluding_skill_caps_score_at_40() -> None:
    j = job(skills=(skill("Python", 3, "required"), skill("Kubernetes", 2, "excluding")))
    result = _engine().match(profile(), j)

    assert result.excluding_cap_applied
    assert result.score <= 40


def test_ut_match_06_missing_skills_sorted_by_priority() -> None:
    p = profile(skills=(skill("Python", 1), skill("Docker", 1)))
    j = job(
        skills=(
            skill("Docker", 3, "desired"),
            skill("Python", 3, "required"),
            skill("SQL", 3, "required"),
            skill("Testing", 2, "desired"),
            skill("Linux", 3, "excluding"),
        )
    )
    gaps = MissingSkillsAnalyzer().analyze(p, j)

    assert [(g.skill, g.priority) for g in gaps] == [
        ("Linux", Priority.HIGH),
        ("SQL", Priority.HIGH),
        ("Python", Priority.MEDIUM),
        ("Testing", Priority.MEDIUM),
        ("Docker", Priority.LOW),
    ]
    python_gap = next(g for g in gaps if g.skill == "Python")
    assert python_gap.gap == 2
    assert python_gap.kind is RequirementKind.REQUIRED


@pytest.mark.parametrize(
    ("years", "expected"),
    [(0.0, 0.0), (1.0, 5.0), (2.0, 10.0), (5.0, 10.0)],
)
def test_experience_years_against_minimum(years: float, expected: float) -> None:
    criterion = ExperienceCriterion(10, relevance_share=0.0)
    j = job(experience=ExperienceRequirement(min_years=2))

    assert criterion.evaluate(profile(years_experience=years), j).earned == expected


@pytest.mark.parametrize(("years", "expected"), [(0.0, 5.0), (0.5, 7.5), (1.0, 10.0)])
def test_experience_without_minimum_uses_reference_years(years: float, expected: float) -> None:
    # Sin mínimo pedido, no tener experiencia resta la mitad (no todo) de la parte de años.
    criterion = ExperienceCriterion(10, reference_years=1.0, relevance_share=0.0)
    j = job(experience=ExperienceRequirement(min_years=0))

    assert criterion.evaluate(profile(years_experience=years), j).earned == expected


def test_experience_relevance_counts_skills_used_at_work() -> None:
    criterion = ExperienceCriterion(10, relevance_share=0.4)
    j = job()  # pide Python, SQL y Docker y 1 año

    relevant = criterion.evaluate(profile(), j)
    assert relevant.earned == 10
    assert relevant.details["relevant_skills"] == ["Docker", "Python", "SQL"]
    # Mismo año de experiencia, pero en algo que la oferta no pide.
    unrelated = criterion.evaluate(profile(experience_skills=frozenset({"excel"})), j)
    assert unrelated.earned == 6
    # Experiencia sin competencias cargadas: la relevancia cuenta la mitad.
    undeclared = criterion.evaluate(profile(experience_skills=frozenset()), j)
    assert undeclared.earned == 8
    # Sin experiencia: no hay relevancia.
    none = criterion.evaluate(profile(years_experience=0, experience_skills=frozenset()), j)
    assert none.earned == 0


def test_experience_now_moves_the_score_more_than_conditions() -> None:
    engine = _engine()
    with_experience = engine.match(profile(), job()).score
    without = engine.match(profile(years_experience=0, experience_skills=frozenset()), job())
    onsite = replace(
        job(), work_conditions=replace(job().work_conditions, work_modality=frozenset({"onsite"}))
    )
    other_modality = engine.match(profile(), onsite).score
    assert with_experience - without.score == 25  # todo el peso de experiencia
    assert with_experience - other_modality < 2  # una condición distinta resta poco


def test_conditions_criterion_averages_known_checks() -> None:
    from app.domain.conditions import WorkModalityCheck, WorkScheduleCheck

    criterion = ConditionsCriterion(10, [WorkModalityCheck(False), WorkScheduleCheck(False)])
    assert criterion.evaluate(profile(), job()).earned == 10
    onsite = replace(
        job(), work_conditions=replace(job().work_conditions, work_modality=frozenset({"onsite"}))
    )
    result = criterion.evaluate(profile(), onsite)
    assert result.earned == 5 and result.details["mismatched"] == 1
    empty = replace(
        profile(),
        work_conditions=replace(
            profile().work_conditions, work_modality=frozenset(), work_schedule=frozenset()
        ),
    )
    assert criterion.evaluate(empty, job()).earned == 10  # sin datos no penaliza


@pytest.mark.parametrize(
    ("have", "need", "expected"),
    [
        (EducationItem("university", "in_progress"), EducationItem("university", "completed"), 2.5),
        (EducationItem("university", "completed"), EducationItem("university", "completed"), 5.0),
        (
            EducationItem("postgraduate", "in_progress"),
            EducationItem("university", "completed"),
            5.0,
        ),
        (EducationItem("secondary", "completed"), EducationItem("tertiary", "in_progress"), 0.0),
    ],
)
def test_education_levels(have: EducationItem, need: EducationItem, expected: float) -> None:
    result = EducationCriterion(5).evaluate(profile(education=(have,)), job(education=(need,)))
    assert result.earned == expected


def test_education_full_when_not_required() -> None:
    assert EducationCriterion(5).evaluate(profile(education=()), job(education=())).earned == 5


def test_languages_half_credit_below_level() -> None:
    criterion = LanguagesCriterion(5)
    j = job(languages=(lang("Inglés", "C1"), lang("Portugués", "B1")))

    # Inglés B2 < C1 => 0.5; Portugués ausente => 0
    assert criterion.evaluate(profile(), j).earned == 1.25
    assert criterion.evaluate(profile(), job(languages=())).earned == 5


def test_language_free_text_levels_are_understood() -> None:
    p = profile(languages=(lang("Inglés", "avanzado"),))
    assert LanguagesCriterion(5).evaluate(p, job(languages=(lang("Inglés", "B2"),))).earned == 5


def test_matched_skills_reported() -> None:
    matched = MissingSkillsAnalyzer().matched(profile(), job())
    assert {m.skill for m in matched} == {"Python", "SQL"}
