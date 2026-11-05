"""Chequeos de condiciones laborales (`conditions_fit`, §7.1 del contrato).

Cada condición es una clase (`ConditionCheck`, OCP). No modifican el score: indican si el
match es compatible (filtros duros) y qué condiciones coinciden o no.
Si falta el dato en alguno de los dos lados, el resultado es `unknown` y no penaliza.
"""

import math
from typing import Protocol

from app.domain.models import (
    CheckOutcome,
    ConditionCheckResult,
    JobOpportunity,
    Location,
    SalaryOutcome,
    StudentProfile,
)
from app.domain.normalization import normalize_text
from app.domain.salary import SalaryComparator
from app.domain.scales import availability_rank, travel_rank


class ConditionCheck(Protocol):
    name: str

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> ConditionCheckResult: ...


def _sorted(values: frozenset[str]) -> list[str]:
    return sorted(values)


def _intersection(
    name: str, hard: bool, have: frozenset[str], want: frozenset[str]
) -> ConditionCheckResult:
    if not have or not want:
        outcome = CheckOutcome.UNKNOWN
    elif have & want:
        outcome = CheckOutcome.MATCH
    else:
        outcome = CheckOutcome.MISMATCH
    return ConditionCheckResult(name, outcome, hard, _sorted(have), _sorted(want))


def haversine_km(a: Location, b: Location) -> float | None:
    if a.lat is None or a.lon is None or b.lat is None or b.lon is None:
        return None
    radius = 6371.0
    phi1, phi2 = math.radians(a.lat), math.radians(b.lat)
    dphi = phi2 - phi1
    dlambda = math.radians(b.lon - a.lon)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return round(2 * radius * math.asin(math.sqrt(h)), 1)


class WorkModalityCheck:
    """Presencialidad (presencial / remota / mixta) y días presenciales en mixta."""

    name = "work_modality"

    def __init__(self, hard: bool) -> None:
        self._hard = hard

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> ConditionCheckResult:
        p, j = profile.work_conditions, job.work_conditions
        base = _intersection(self.name, self._hard, p.work_modality, j.work_modality)
        common = p.work_modality & j.work_modality
        if (
            base.result is CheckOutcome.MATCH
            and common == frozenset({"hybrid"})
            and p.hybrid_onsite_days is not None
            and j.hybrid_onsite_days is not None
            and j.hybrid_onsite_days > p.hybrid_onsite_days
        ):
            return ConditionCheckResult(
                self.name,
                CheckOutcome.PARTIAL,
                self._hard,
                base.profile_value,
                base.job_value,
                {
                    "profile_max_onsite_days": p.hybrid_onsite_days,
                    "job_onsite_days": j.hybrid_onsite_days,
                },
            )
        return base


class LocationCheck:
    """Ubicación/traslado: sólo aplica si el puesto tiene presencialidad (onsite o hybrid)."""

    name = "location"

    def __init__(self, hard: bool) -> None:
        self._hard = hard

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> ConditionCheckResult:
        p_loc, j_loc = profile.location, job.location
        p_val = {"city": p_loc.city, "province": p_loc.province, "country": p_loc.country}
        j_val = {"city": j_loc.city, "province": j_loc.province, "country": j_loc.country}
        modalities = job.work_conditions.work_modality
        if modalities and modalities <= frozenset({"remote"}):
            return ConditionCheckResult(
                self.name, CheckOutcome.MATCH, self._hard, p_val, j_val, {"reason": "remote"}
            )
        if p_loc.is_empty or j_loc.is_empty:
            return ConditionCheckResult(self.name, CheckOutcome.UNKNOWN, self._hard, p_val, j_val)

        relocation = (
            profile.work_conditions.willing_to_relocate or job.work_conditions.relocation_support
        )
        distance = haversine_km(p_loc, j_loc)
        max_km = profile.work_conditions.max_commute_km
        details: dict[str, object] = {"distance_km": distance}

        if distance is not None and max_km is not None:
            outcome = CheckOutcome.MATCH if distance <= max_km else CheckOutcome.MISMATCH
        elif normalize_text(p_loc.country) != normalize_text(j_loc.country):
            outcome = CheckOutcome.MISMATCH
        elif normalize_text(p_loc.city) == normalize_text(j_loc.city) and p_loc.city:
            outcome = CheckOutcome.MATCH
        elif normalize_text(p_loc.province) == normalize_text(j_loc.province) and p_loc.province:
            outcome = CheckOutcome.PARTIAL
        else:
            outcome = CheckOutcome.MISMATCH

        if outcome is CheckOutcome.MISMATCH and relocation:
            outcome = CheckOutcome.PARTIAL
            details["relocation"] = True
        return ConditionCheckResult(self.name, outcome, self._hard, p_val, j_val, details)


class WorkScheduleCheck:
    """Modalidad horaria (full/part time) y solapamiento de horas semanales."""

    name = "work_schedule"

    def __init__(self, hard: bool) -> None:
        self._hard = hard

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> ConditionCheckResult:
        p, j = profile.work_conditions, job.work_conditions
        base = _intersection(self.name, self._hard, p.work_schedule, j.work_schedule)
        if base.result is CheckOutcome.MISMATCH or p.weekly_hours is None or j.weekly_hours is None:
            return base
        overlap = (
            p.weekly_hours.max >= j.weekly_hours.min and j.weekly_hours.max >= p.weekly_hours.min
        )
        outcome = base.result if overlap else CheckOutcome.MISMATCH
        if base.result is CheckOutcome.UNKNOWN and overlap:
            outcome = CheckOutcome.MATCH
        return ConditionCheckResult(
            self.name,
            outcome,
            self._hard,
            {"work_schedule": base.profile_value, "weekly_hours": vars(p.weekly_hours)},
            {"work_schedule": base.job_value, "weekly_hours": vars(j.weekly_hours)},
        )


class ShiftsCheck:
    """Franjas del puesto frente a las disponibles y al turno en que cursa el estudiante."""

    name = "shifts"

    def __init__(self, hard: bool) -> None:
        self._hard = hard

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> ConditionCheckResult:
        have = profile.work_conditions.shifts
        want = job.work_conditions.shifts
        study = profile.academic.student_shift
        p_val = {"shifts": _sorted(have), "student_shift": _sorted(study)}
        if not want:
            return ConditionCheckResult(self.name, CheckOutcome.UNKNOWN, self._hard, p_val, [])
        if want & study:
            return ConditionCheckResult(
                self.name,
                CheckOutcome.MISMATCH,
                self._hard,
                p_val,
                _sorted(want),
                {"conflict_with_study": _sorted(want & study)},
            )
        if not have:
            return ConditionCheckResult(
                self.name, CheckOutcome.UNKNOWN, self._hard, p_val, _sorted(want)
            )
        if want <= have:
            outcome = CheckOutcome.MATCH
        elif want & have:
            outcome = CheckOutcome.PARTIAL
        else:
            outcome = CheckOutcome.MISMATCH
        return ConditionCheckResult(self.name, outcome, self._hard, p_val, _sorted(want))


class EmploymentTypeCheck:
    """Tipo de vínculo: relación de dependencia, freelance, pasantía, trainee."""

    name = "employment_type"

    def __init__(self, hard: bool) -> None:
        self._hard = hard

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> ConditionCheckResult:
        return _intersection(
            self.name,
            self._hard,
            profile.work_conditions.employment_type,
            job.work_conditions.employment_type,
        )


class ContractDurationCheck:
    name = "contract_duration"

    def __init__(self, hard: bool) -> None:
        self._hard = hard

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> ConditionCheckResult:
        return _intersection(
            self.name,
            self._hard,
            profile.work_conditions.contract_duration,
            job.work_conditions.contract_duration,
        )


class AvailabilityStartCheck:
    """El estudiante puede empezar antes o cuando lo necesita la oferta."""

    name = "availability_start"

    def __init__(self, hard: bool) -> None:
        self._hard = hard

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> ConditionCheckResult:
        p_val = profile.work_conditions.availability_start
        j_val = job.work_conditions.availability_start
        p_rank, j_rank = availability_rank(p_val), availability_rank(j_val)
        if p_rank is None or j_rank is None:
            outcome = CheckOutcome.UNKNOWN
        elif p_rank <= j_rank:
            outcome = CheckOutcome.MATCH
        else:
            outcome = CheckOutcome.PARTIAL
        return ConditionCheckResult(self.name, outcome, self._hard, p_val, j_val)


class SalaryCheck:
    """Sueldo pretendido ↔ ofrecido. El detalle completo va en `conditions_fit.salary_fit`."""

    name = "salary"

    def __init__(self, hard: bool, comparator: SalaryComparator) -> None:
        self._hard = hard
        self._comparator = comparator

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> ConditionCheckResult:
        p, j = profile.work_conditions, job.work_conditions
        fit = self._comparator.compare(
            p.salary,
            j.salary,
            expected_weekly_hours=p.weekly_hours.max if p.weekly_hours else None,
            offered_weekly_hours=j.weekly_hours.max if j.weekly_hours else None,
        )
        outcome = {
            SalaryOutcome.MATCH: CheckOutcome.MATCH,
            SalaryOutcome.PARTIAL: CheckOutcome.PARTIAL,
            SalaryOutcome.BELOW_EXPECTATION: CheckOutcome.MISMATCH,
            SalaryOutcome.UNKNOWN: CheckOutcome.UNKNOWN,
        }[fit.result]
        return ConditionCheckResult(
            self.name,
            outcome,
            self._hard,
            details={"salary_fit": fit},
        )


class TravelCheck:
    name = "travel"

    def __init__(self, hard: bool) -> None:
        self._hard = hard

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> ConditionCheckResult:
        p_val = profile.work_conditions.travel_availability
        j_val = job.work_conditions.travel_availability
        p_rank, j_rank = travel_rank(p_val), travel_rank(j_val)
        if j_rank == 0:
            outcome = CheckOutcome.MATCH
        elif p_rank is None or j_rank is None:
            outcome = CheckOutcome.UNKNOWN
        else:
            outcome = CheckOutcome.MATCH if p_rank >= j_rank else CheckOutcome.MISMATCH
        return ConditionCheckResult(self.name, outcome, self._hard, p_val, j_val)


class DriverLicenseCheck:
    """Licencias y vehículo propio: sólo se evalúa si la oferta los exige."""

    name = "driver_license"

    def __init__(self, hard: bool) -> None:
        self._hard = hard

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> ConditionCheckResult:
        p, j = profile.work_conditions, job.work_conditions
        p_val = {"driver_license": _sorted(p.driver_license), "own_vehicle": p.own_vehicle}
        j_val = {"driver_license": _sorted(j.driver_license), "own_vehicle": j.own_vehicle}
        needs_vehicle = j.own_vehicle is True
        if not j.driver_license and not needs_vehicle:
            return ConditionCheckResult(self.name, CheckOutcome.MATCH, self._hard, p_val, j_val)
        license_ok = j.driver_license <= p.driver_license
        if needs_vehicle and p.own_vehicle is None:
            outcome = CheckOutcome.UNKNOWN if license_ok else CheckOutcome.MISMATCH
        else:
            vehicle_ok = not needs_vehicle or p.own_vehicle is True
            outcome = CheckOutcome.MATCH if license_ok and vehicle_ok else CheckOutcome.MISMATCH
        return ConditionCheckResult(self.name, outcome, self._hard, p_val, j_val)


class WorkAuthorizationCheck:
    """Países donde puede trabajar el estudiante frente a los que admite la oferta."""

    name = "work_authorization"

    def __init__(self, hard: bool) -> None:
        self._hard = hard

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> ConditionCheckResult:
        want = job.work_conditions.work_authorization
        have = profile.work_conditions.work_authorization
        if not want:
            return ConditionCheckResult(
                self.name, CheckOutcome.MATCH, self._hard, _sorted(have), []
            )
        return _intersection(self.name, self._hard, have, want)


class AcademicCheck:
    """Avance de carrera, año de cursada y carreras admitidas por la oferta."""

    name = "academic"

    def __init__(self, hard: bool) -> None:
        self._hard = hard

    def evaluate(self, profile: StudentProfile, job: JobOpportunity) -> ConditionCheckResult:
        req, have = job.academic, profile.academic
        p_val = {
            "career": have.career,
            "current_year": have.current_year,
            "progress_percent": have.progress_percent,
        }
        j_val = {
            "careers": list(req.careers),
            "min_current_year": req.min_current_year,
            "min_progress_percent": req.min_progress_percent,
        }
        verdicts: list[bool | None] = []
        if req.min_progress_percent is not None:
            verdicts.append(
                None
                if have.progress_percent is None
                else have.progress_percent >= req.min_progress_percent
            )
        if req.min_current_year is not None:
            verdicts.append(
                None if have.current_year is None else have.current_year >= req.min_current_year
            )
        if req.careers:
            careers = {normalize_text(c) for c in req.careers}
            verdicts.append(None if not have.career else normalize_text(have.career) in careers)

        if not verdicts:
            outcome = CheckOutcome.MATCH
        elif False in verdicts:
            outcome = CheckOutcome.MISMATCH
        elif None in verdicts:
            outcome = CheckOutcome.UNKNOWN
        else:
            outcome = CheckOutcome.MATCH
        return ConditionCheckResult(self.name, outcome, self._hard, p_val, j_val)
