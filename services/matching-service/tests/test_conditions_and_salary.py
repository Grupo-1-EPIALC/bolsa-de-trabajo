"""UT-MATCH-07 y UT-MATCH-08: condiciones laborales y sueldo pretendido/ofrecido."""

from dataclasses import replace
from typing import Any

import pytest

from app.domain.conditions import (
    AcademicCheck,
    AvailabilityStartCheck,
    DriverLicenseCheck,
    LocationCheck,
    ShiftsCheck,
    TravelCheck,
    WorkAuthorizationCheck,
    WorkModalityCheck,
    WorkScheduleCheck,
    haversine_km,
)
from app.domain.engine import build_engine
from app.domain.models import (
    AcademicRequirement,
    CheckOutcome,
    HoursRange,
    JobOpportunity,
    Location,
    SalaryOutcome,
    SalaryRange,
    StudentProfile,
)
from app.domain.rules import SalaryRules, ScoringRules
from app.domain.salary import SalaryComparator
from tests.builders import job, profile


def _wc[T: (StudentProfile, JobOpportunity)](entity: T, **changes: Any) -> T:
    return replace(entity, work_conditions=replace(entity.work_conditions, **changes))


def test_ut_match_07_hard_mismatch_makes_match_incompatible() -> None:
    engine = build_engine(ScoringRules(), lambda: "now")
    onsite_only = _wc(job(), work_modality=frozenset({"onsite"}))
    result = engine.match(profile(), onsite_only)

    assert not result.conditions_fit.compatible
    modality = next(c for c in result.conditions_fit.checks if c.condition == "work_modality")
    assert modality.result is CheckOutcome.MISMATCH and modality.hard
    # Las condiciones no tocan el score
    assert result.score == engine.match(profile(), job()).score


def test_compatible_match_reports_distance_and_salary_fit() -> None:
    result = build_engine(ScoringRules(), lambda: "now").match(profile(), job())

    assert result.conditions_fit.compatible
    assert result.conditions_fit.distance_km is not None
    assert result.conditions_fit.salary_fit is not None
    assert result.conditions_fit.salary_fit.result is SalaryOutcome.MATCH


def test_modality_partial_when_too_many_onsite_days() -> None:
    j = _wc(job(), hybrid_onsite_days=5)
    assert WorkModalityCheck(True).evaluate(profile(), j).result is CheckOutcome.PARTIAL


def test_modality_unknown_when_missing() -> None:
    p = _wc(profile(), work_modality=frozenset())
    assert WorkModalityCheck(True).evaluate(p, job()).result is CheckOutcome.UNKNOWN


def test_location_remote_always_matches() -> None:
    j = _wc(job(location=Location()), work_modality=frozenset({"remote"}))
    assert LocationCheck(True).evaluate(profile(), j).result is CheckOutcome.MATCH


def test_location_uses_distance_and_commute_limit() -> None:
    far = job(
        location=Location(country="AR", province="Córdoba", city="Córdoba", lat=-31.42, lon=-64.19)
    )
    check = LocationCheck(True)

    assert check.evaluate(profile(), job()).result is CheckOutcome.MATCH
    assert check.evaluate(profile(), far).result is CheckOutcome.MISMATCH
    relocating = _wc(profile(), willing_to_relocate=True)
    assert check.evaluate(relocating, far).result is CheckOutcome.PARTIAL


def test_location_falls_back_to_city_and_province() -> None:
    p = profile(location=Location(country="AR", province="Buenos Aires", city="San Isidro"))
    p = _wc(p, max_commute_km=None)
    check = LocationCheck(True)

    same_city = job(location=Location(country="AR", province="Buenos Aires", city="San Isidro"))
    same_prov = job(location=Location(country="AR", province="Buenos Aires", city="Tigre"))
    other = job(location=Location(country="UY", province="Montevideo", city="Montevideo"))
    assert check.evaluate(p, same_city).result is CheckOutcome.MATCH
    assert check.evaluate(p, same_prov).result is CheckOutcome.PARTIAL
    assert check.evaluate(p, other).result is CheckOutcome.MISMATCH
    assert check.evaluate(profile(location=Location()), job()).result is CheckOutcome.UNKNOWN


def test_haversine_known_distance() -> None:
    caba = Location(lat=-34.6037, lon=-58.3816)
    cordoba = Location(lat=-31.4201, lon=-64.1888)
    distance = haversine_km(caba, cordoba)
    assert distance is not None and 640 < distance < 660
    assert haversine_km(caba, Location()) is None


def test_schedule_checks_weekly_hours_overlap() -> None:
    check = WorkScheduleCheck(True)
    assert check.evaluate(profile(), job()).result is CheckOutcome.MATCH
    short = _wc(profile(), weekly_hours=HoursRange(10, 20))
    assert check.evaluate(short, job()).result is CheckOutcome.MISMATCH
    part_time_only = _wc(job(), work_schedule=frozenset({"hourly"}))
    assert check.evaluate(profile(), part_time_only).result is CheckOutcome.MISMATCH


def test_shifts_conflict_with_study_shift() -> None:
    check = ShiftsCheck(False)
    assert check.evaluate(profile(), job()).result is CheckOutcome.MATCH
    evening = _wc(job(), shifts=frozenset({"evening"}))
    result = check.evaluate(profile(), evening)
    assert result.result is CheckOutcome.MISMATCH
    assert result.details["conflict_with_study"] == ["evening"]
    mixed = _wc(job(), shifts=frozenset({"morning", "night"}))
    assert check.evaluate(profile(), mixed).result is CheckOutcome.PARTIAL


@pytest.mark.parametrize(
    ("have", "need", "expected"),
    [
        ("immediate", "within_15_days", CheckOutcome.MATCH),
        ("within_30_days", "immediate", CheckOutcome.PARTIAL),
        ("to_agree", "immediate", CheckOutcome.UNKNOWN),
    ],
)
def test_availability_start(have: str, need: str, expected: CheckOutcome) -> None:
    p = _wc(profile(), availability_start=have)
    j = _wc(job(), availability_start=need)
    assert AvailabilityStartCheck(False).evaluate(p, j).result is expected


def test_travel_driver_license_and_authorization() -> None:
    p = _wc(
        profile(),
        travel_availability="occasional",
        driver_license=frozenset({"B1"}),
        own_vehicle=False,
        work_authorization=frozenset({"AR"}),
    )
    frequent = _wc(job(), travel_availability="frequent")
    assert TravelCheck(False).evaluate(p, frequent).result is CheckOutcome.MISMATCH
    assert TravelCheck(False).evaluate(p, _wc(job(), travel_availability="none")).result is (
        CheckOutcome.MATCH
    )

    needs_car = _wc(job(), driver_license=frozenset({"B1"}), own_vehicle=True)
    assert DriverLicenseCheck(True).evaluate(p, needs_car).result is CheckOutcome.MISMATCH
    assert DriverLicenseCheck(True).evaluate(p, job()).result is CheckOutcome.MATCH

    uy_only = _wc(job(), work_authorization=frozenset({"UY"}))
    assert WorkAuthorizationCheck(True).evaluate(p, uy_only).result is CheckOutcome.MISMATCH
    assert WorkAuthorizationCheck(True).evaluate(p, job()).result is CheckOutcome.MATCH


def test_academic_requirements() -> None:
    check = AcademicCheck(False)
    ok = job(
        academic=AcademicRequirement(min_progress_percent=50, careers=("Ingeniería en Sistemas",))
    )
    too_high = job(academic=AcademicRequirement(min_current_year=5))
    assert check.evaluate(profile(), ok).result is CheckOutcome.MATCH
    assert check.evaluate(profile(), too_high).result is CheckOutcome.MISMATCH
    assert check.evaluate(profile(), job()).result is CheckOutcome.MATCH


# -------------------------------------------------------------- sueldo ---


def _cmp(**rules: float) -> SalaryComparator:
    return SalaryComparator(SalaryRules(**rules))  # type: ignore[arg-type]


def test_ut_match_08_salary_overlap_is_match() -> None:
    fit = _cmp().compare(
        SalaryRange(min=700000, currency="ARS"), SalaryRange(min=500000, max=800000, currency="ARS")
    )
    assert fit.result is SalaryOutcome.MATCH
    assert fit.gap_percent == 0


def test_salary_gap_within_tolerance_is_partial() -> None:
    fit = _cmp().compare(
        SalaryRange(min=1000000, currency="ARS"),
        SalaryRange(min=800000, max=950000, currency="ARS"),
    )
    assert fit.result is SalaryOutcome.PARTIAL
    assert fit.gap_percent == 5.0


def test_salary_below_expectation_unless_negotiable() -> None:
    expected = SalaryRange(min=1000000, currency="ARS")
    offered = SalaryRange(max=700000, currency="ARS")
    assert _cmp().compare(expected, offered).result is SalaryOutcome.BELOW_EXPECTATION
    negotiable = replace(offered, negotiable=True)
    assert _cmp().compare(expected, negotiable).result is SalaryOutcome.PARTIAL


def test_salary_normalizes_periods_and_net() -> None:
    comparator = _cmp()
    hourly = comparator.to_monthly_gross(SalaryRange(min=10, max=10, period="hour"), 20)
    yearly = comparator.to_monthly_gross(SalaryRange(min=1300, max=1300, period="year"), None)
    net = comparator.to_monthly_gross(SalaryRange(min=100, max=100, gross=False), None)
    assert hourly is not None and hourly.min == 866.0
    assert yearly is not None and yearly.min == 100.0
    assert net is not None and net.min == 121.0
    assert comparator.to_monthly_gross(SalaryRange(min=1, period="project"), None) is None


def test_salary_unknown_cases() -> None:
    usd = SalaryRange(min=1000, currency="USD")
    ars = SalaryRange(min=1000000, currency="ARS")
    assert _cmp().compare(usd, ars).result is SalaryOutcome.UNKNOWN
    assert _cmp().compare(SalaryRange(to_agree=True), ars).result is SalaryOutcome.UNKNOWN
    assert _cmp().compare(None, ars).result is SalaryOutcome.UNKNOWN


def test_salary_converts_currency_with_fx_rate() -> None:
    comparator = SalaryComparator(SalaryRules(fx_rates={"USD_ARS": 1000.0}))
    fit = comparator.compare(
        SalaryRange(min=900, currency="USD"), SalaryRange(min=800000, max=1000000, currency="ARS")
    )
    assert fit.result is SalaryOutcome.MATCH
    assert fit.currency == "ARS"
