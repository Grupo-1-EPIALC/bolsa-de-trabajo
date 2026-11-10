"""UT-MATCH-13: diccionario de competencias (alias, equivalentes, implicaciones y similares)."""

import json

import pytest

from app.domain.engine import build_engine
from app.domain.errors import InvalidRulesError
from app.domain.models import ExperienceRequirement, RequirementKind, SkillItem
from app.domain.rules import ScoringRules
from app.domain.skill_dictionary import SkillDictionary, SkillEntry, SkillGroup, SkillRelation
from app.domain.skill_gaps import SkillGapAggregator
from app.infrastructure.config import DATA_DIR
from app.infrastructure.rules_loader import load_skill_dictionary, skill_dictionary_from_mapping
from tests.builders import job, profile

SKILLS = load_skill_dictionary(DATA_DIR / "skill_dictionary.json")


def _skill(name: str, level: int = 3, kind: str = "required") -> SkillItem:
    return SkillItem(name, SKILLS.normalize(name), level, kind=RequirementKind(kind))


def test_ut_match_13_aliases_with_typos_and_accents() -> None:
    for alias in ("Postgres", "PostgreSQL", "posgres", "PosgreSQL", "psql", "Postgre SQL"):
        assert SKILLS.normalize(alias) == "postgresql", alias
    assert SKILLS.normalize("Node") == "node.js"
    assert SKILLS.normalize("Metodologías ágiles") == "agile"
    assert SKILLS.normalize("Spring Boot") == "spring"
    assert SKILLS.normalize("Cobol 85") == "cobol 85"  # desconocida: texto normalizado


def test_equivalent_counts_fully_and_implied_uses_the_level() -> None:
    mariadb = SKILLS.coverage({"mariadb": 4}, "mysql")
    assert mariadb is not None and mariadb.full
    assert mariadb.relation is SkillRelation.EQUIVALENT
    sql = SKILLS.coverage({"postgresql": 4}, "sql")
    assert sql is not None and sql.relation is SkillRelation.IMPLIED and sql.level == 4
    # Implicación transitiva: Next.js ⇒ React ⇒ JavaScript.
    js = SKILLS.coverage({"next.js": 2}, "javascript")
    assert js is not None and js.full and js.via == "next.js"
    # No es simétrica: saber SQL no implica PostgreSQL.
    assert SKILLS.coverage({"sql": 5}, "postgresql") is None


def test_similar_tool_gives_partial_credit() -> None:
    gitlab = SKILLS.coverage({"github": 3}, "gitlab")
    assert gitlab is not None and not gitlab.full
    assert gitlab.relation is SkillRelation.SIMILAR and gitlab.credit == 0.75
    # Lo exacto gana a lo similar.
    both = SKILLS.coverage({"github": 1, "gitlab": 2}, "gitlab")
    assert both is not None and both.relation is SkillRelation.EXACT


def test_engine_uses_the_dictionary() -> None:
    engine = build_engine(ScoringRules(), lambda: "now", SKILLS)
    p = profile(
        skills=(
            _skill("Posgres", 3),
            _skill("MariaDB", 3),
            _skill("GitHub", 3),
            _skill("Python", 3),
        ),
        experience_skills=frozenset({"postgresql"}),
    )
    j = job(
        skills=(
            _skill("SQL", 3),
            _skill("MySQL", 3),
            _skill("GitLab", 2),
            _skill("Python", 3, "excluding"),
        ),
        experience=ExperienceRequirement(min_years=1),
    )
    result = engine.match(p, j)
    required = next(b for b in result.breakdown if b.criterion == "required_skills")
    assert required.details["matched"] == 3 and required.details["similar"] == 1
    assert required.earned == round(40 * (3 + 0.75) / 4, 2)
    matched = {m.skill: m for m in result.matched_skills}
    assert matched["SQL"].via == "PostgreSQL" and matched["SQL"].relation == "implied"
    assert matched["MySQL"].via == "MariaDB" and matched["MySQL"].relation == "equivalent"
    assert matched["Python"].via == "" and matched["Python"].relation == "exact"
    missing = {m.skill: m for m in result.missing_skills}
    assert missing["GitLab"].similar_to == "GitHub" and missing["GitLab"].credit == 0.75
    assert not result.excluding_cap_applied
    experience = next(b for b in result.breakdown if b.criterion == "experience")
    assert "SQL" in experience.details["relevant_skills"]  # PostgreSQL en la experiencia


def test_excluding_is_not_covered_by_a_similar_tool() -> None:
    engine = build_engine(ScoringRules(), lambda: "now", SKILLS)
    p = profile(skills=(_skill("GitHub", 4),))
    j = job(skills=(_skill("GitLab", 2, "excluding"),))
    assert engine.match(p, j).excluding_cap_applied


def test_gaps_group_by_dictionary_key_and_keep_the_bridge() -> None:
    engine = build_engine(ScoringRules(), lambda: "now", SKILLS)
    p = profile(skills=(_skill("GitHub", 3),))
    results = [
        engine.match(p, job(id="a", skills=(_skill("GitLab", 2),))),
        engine.match(p, job(id="b", skills=(SkillItem("Git Lab", "gitlab", 2),))),
    ]
    gaps = SkillGapAggregator(SKILLS).aggregate(results, 5)
    assert len(gaps) == 1 and gaps[0].jobs_count == 2 and gaps[0].similar_to == "GitHub"


def test_describe_for_the_agent() -> None:
    info = SKILLS.describe("Posgres", have=["MariaDB", "GitHub"])
    assert info["key"] == "postgresql" and info["known"]
    assert "SQL" in info["implies"]
    similar = info["similar"]
    assert isinstance(similar, list) and any(s["skill"] == "MySQL" for s in similar)
    assert info["covered_by"] == {
        "relation": "similar",
        "credit": 0.5,
        "via": "MariaDB",
        "full": False,
    }
    unknown = SKILLS.describe("Lenguaje Inventado")
    assert not unknown["known"] and unknown["equivalents"] == []
    assert "covered_by" not in unknown


def test_dictionary_file_is_consistent() -> None:
    raw = json.loads((DATA_DIR / "skill_dictionary.json").read_text(encoding="utf-8"))
    assert len(raw["skills"]) >= 100
    assert {g["kind"] for g in raw["groups"]} == {"equivalent", "similar"}
    assert all(0 < g["credit"] <= 1 for g in raw["groups"])


def test_invalid_dictionaries_are_rejected() -> None:
    a, b = SkillEntry("a", "A", aliases=("x",)), SkillEntry("b", "B", aliases=("x",))
    with pytest.raises(InvalidRulesError, match="dos skills"):
        SkillDictionary((a, b))
    with pytest.raises(InvalidRulesError, match="no están"):
        SkillDictionary((SkillEntry("a", "A"),), implies={"a": frozenset({"zz"})})
    with pytest.raises(InvalidRulesError, match="crédito"):
        SkillDictionary(
            (SkillEntry("a", "A"), SkillEntry("b", "B")),
            (SkillGroup(SkillRelation.SIMILAR, frozenset({"a", "b"}), credit=0),),
        )
    with pytest.raises(InvalidRulesError, match="normalizada"):
        SkillDictionary((SkillEntry("Python", "Python"),))
    with pytest.raises(InvalidRulesError):
        skill_dictionary_from_mapping({"groups": [{"kind": "otro", "skills": []}]})
