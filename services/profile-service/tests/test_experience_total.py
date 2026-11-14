"""UT-PROF-10: la experiencia total une los períodos superpuestos (no los suma)."""

from app.domain.experience import total_experience_months
from app.domain.profile import Experience


def job(start: str, months: int | None, company: str = "Empresa Ficticia") -> Experience:
    return Experience(company=company, role="Puesto", start=start, months=months)


def test_ut_prof_10_trabajos_simultaneos_cuentan_una_vez() -> None:
    # Caso real (datos ficticios): sumando daba 730 meses (60 años) para 33 años de trayectoria.
    experience = [
        job("1994", 24),  # 1994-1995
        job("1996", 36),  # 1996-1998
        job("1996", 36),  # otro empleo en el mismo período
        job("1998", 347),  # 1998-actual (nov. 2026)
        job("2005", 263),  # 2005-actual, en paralelo
        job("2009", 24),  # 2009-2010, en paralelo
    ]
    assert sum(e.months or 0 for e in experience) == 730
    assert total_experience_months(experience) == 24 + 371  # 1994-1995 y 1996-actual


def test_ut_prof_10_periodos_separados_y_datos_incompletos() -> None:
    assert total_experience_months([]) == 0
    assert total_experience_months([job("2020-03", 12), job("2022-01", 6)]) == 18
    # Consecutivos se unen sin hueco; sin meses o sin inicio válido no cuentan.
    assert total_experience_months([job("2020-01", 12), job("2021-01", 12)]) == 24
    assert total_experience_months([job("2020", None), job("hace años", 10)]) == 0
