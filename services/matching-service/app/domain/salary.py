"""Comparación sueldo pretendido ↔ ofrecido (§7.2 del contrato).

1. Normaliza ambos lados a mensual bruto.
2. Convierte moneda sólo si hay tipo de cambio configurado.
3. `match` si el máximo ofrecido llega al piso pretendido; `partial` si la brecha está dentro
   de la tolerancia o alguna parte acepta negociar; si no, `below_expectation`.
"""

from app.domain.models import HoursRange, SalaryFit, SalaryOutcome, SalaryRange
from app.domain.rules import SalaryRules


class SalaryComparator:
    def __init__(self, rules: SalaryRules) -> None:
        self._rules = rules

    def compare(
        self,
        expected: SalaryRange | None,
        offered: SalaryRange | None,
        expected_weekly_hours: float | None = None,
        offered_weekly_hours: float | None = None,
    ) -> SalaryFit:
        if expected is None or offered is None or not expected.has_amount or not offered.has_amount:
            return SalaryFit(result=SalaryOutcome.UNKNOWN)
        exp = self.to_monthly_gross(expected, expected_weekly_hours)
        off = self.to_monthly_gross(offered, offered_weekly_hours)
        if exp is None or off is None:
            return SalaryFit(result=SalaryOutcome.UNKNOWN)

        currency = offered.currency or expected.currency
        if expected.currency and offered.currency and expected.currency != offered.currency:
            rate = self._rules.fx_rates.get(f"{expected.currency}_{offered.currency}")
            if rate is None:
                return SalaryFit(
                    result=SalaryOutcome.UNKNOWN,
                    expected_monthly=exp,
                    offered_monthly=off,
                    currency="",
                )
            exp = HoursRange(min=round(exp.min * rate, 2), max=round(exp.max * rate, 2))

        if off.max >= exp.min:
            return SalaryFit(SalaryOutcome.MATCH, exp, off, 0.0, currency)

        gap = round((exp.min - off.max) / exp.min * 100, 2) if exp.min > 0 else 0.0
        negotiable = expected.negotiable or offered.negotiable
        outcome = (
            SalaryOutcome.PARTIAL
            if gap <= self._rules.tolerance_percent or negotiable
            else SalaryOutcome.BELOW_EXPECTATION
        )
        return SalaryFit(outcome, exp, off, gap, currency)

    def to_monthly_gross(
        self, salary: SalaryRange, weekly_hours: float | None
    ) -> HoursRange | None:
        low = salary.min if salary.min is not None else salary.max
        high = salary.max if salary.max is not None else salary.min
        if low is None or high is None:
            return None
        factor = self._period_factor(salary.period, weekly_hours)
        if factor is None:
            return None
        if not salary.gross:
            factor *= self._rules.net_to_gross
        return HoursRange(min=round(low * factor, 2), max=round(high * factor, 2))

    def _period_factor(self, period: str, weekly_hours: float | None) -> float | None:
        hours = weekly_hours or self._rules.default_weekly_hours
        factors: dict[str, float] = {
            "month": 1.0,
            "hour": hours * self._rules.weeks_per_month,
            "day": self._rules.working_days_per_month,
            # Anual -> mensual: 12 sueldos + aguinaldo (configurable en salaries_per_year)
            "year": 1.0 / self._rules.salaries_per_year,
        }
        # `project` (y cualquier período desconocido) no se convierte => unknown
        return factors.get(period)
