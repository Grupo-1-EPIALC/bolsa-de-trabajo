"""Experiencia total por reglas: los períodos superpuestos se cuentan una sola vez.

Sumar los meses de cada experiencia infla el total cuando hay trabajos simultáneos (por ejemplo,
dos empleos de 1998 a hoy contaban doble). Se usa en la vista para matching (`years_experience`,
criterio de Experiencia) y en el resumen que recibe la IA del diseño del CV.
"""

import re
from collections.abc import Iterable

from app.domain.profile import Experience

_YEAR_MONTH = re.compile(r"(\d{4})(?:-(\d{1,2}))?")


def _start_index(start: str) -> int | None:
    """Mes absoluto (año * 12 + mes - 1) del inicio; sin mes = enero, como `months`."""
    match = _YEAR_MONTH.fullmatch(start.strip())
    if not match:
        return None
    return int(match.group(1)) * 12 + int(match.group(2) or 1) - 1


def total_experience_months(experience: Iterable[Experience]) -> int:
    """Meses trabajados en total, uniendo los períodos que se superponen.

    Cada período va del inicio a `inicio + months - 1` (`months` ya lo calculó el servicio con la
    fecha de fin o "actual"). Las experiencias sin `months` o sin inicio válido no cuentan.
    """
    spans = sorted(
        (first, first + e.months - 1)
        for e in experience
        if e.months and (first := _start_index(e.start)) is not None
    )
    total = 0
    current: tuple[int, int] | None = None
    for first, last in spans:
        if current is None or first > current[1] + 1:
            if current is not None:
                total += current[1] - current[0] + 1
            current = (first, last)
        else:
            current = (current[0], max(current[1], last))
    if current is not None:
        total += current[1] - current[0] + 1
    return total
