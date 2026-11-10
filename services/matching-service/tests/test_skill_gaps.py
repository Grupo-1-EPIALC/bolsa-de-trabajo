"""UT-MATCH-12: qué competencias sumar o mejorar en general (sobre las ofertas parecidas)."""

from app.domain.models import (
    ConditionsFit,
    MatchResult,
    MissingSkill,
    Priority,
    RequirementKind,
)
from app.domain.skill_gaps import SkillGapAggregator

REQ, DES = RequirementKind.REQUIRED, RequirementKind.DESIRED


def _miss(skill: str, kind: RequirementKind, current: int = 0, required: int = 3) -> MissingSkill:
    return MissingSkill(skill, kind, required, current, required - current, Priority.HIGH)


def _result(job_id: str, *missing: MissingSkill) -> MatchResult:
    return MatchResult(
        profile_id="stu",
        job_id=job_id,
        score=70,
        excluding_cap_applied=False,
        breakdown=(),
        missing_skills=missing,
        matched_skills=(),
        conditions_fit=ConditionsFit(True),
        engine_version="2.0.0",
        rules_version="2.0.0",
        computed_at="now",
    )


def test_ut_match_12_gaps_are_aggregated_over_similar_jobs() -> None:
    results = [
        _result("j1", _miss("Docker", REQ), _miss("Inglés técnico", DES)),
        _result("j2", _miss("docker", REQ, current=0, required=4), _miss("SQL", REQ, current=2)),
        _result("j3", _miss("Docker", DES), _miss("Kubernetes", DES)),
        _result("j4", _miss("Kubernetes", DES)),
    ]
    gaps = SkillGapAggregator().aggregate(results, max_gaps=10)
    by_skill = {g.skill.lower(): g for g in gaps}

    docker = by_skill["docker"]
    # Se cuenta una vez por oferta, sin importar mayúsculas, y se toma el nivel más alto.
    assert docker.jobs_count == 3 and docker.share == 0.75
    assert docker.required_in == 2 and docker.required_level == 4
    assert docker.priority is Priority.HIGH and docker.status == "missing"
    # Deseable en la mitad de las ofertas => media.
    assert by_skill["kubernetes"].priority is Priority.MEDIUM
    # Obligatoria en una sola oferta, pero ya la tiene con nivel menor => media y "improve".
    sql = by_skill["sql"]
    assert sql.priority is Priority.MEDIUM and sql.status == "improve" and sql.current_level == 2
    # Deseable en una sola oferta => baja.
    assert by_skill["inglés técnico"].priority is Priority.LOW
    # Orden: prioridad y después cuántas ofertas la piden.
    assert [g.skill for g in gaps][:2] == ["Docker", "Kubernetes"]


def test_gaps_respect_max_and_empty_input() -> None:
    results = [_result("j1", *(_miss(f"S{i}", REQ) for i in range(12)))]
    assert len(SkillGapAggregator().aggregate(results, max_gaps=8)) == 8
    assert SkillGapAggregator().aggregate([], max_gaps=8) == []
