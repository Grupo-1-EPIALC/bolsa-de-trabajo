"""Postulaciones de estudiantes a ofertas (sin dependencias de frameworks).

Al postularse, el estudiante comparte con la empresa dueña de la oferta su nombre, email,
teléfono y título. jobs-service guarda una copia (`ApplicantSnapshot`) tomada del perfil en
profile-service en ese momento; volver a postularse la refresca. Retirar la postulación la
borra: la empresa deja de ver al estudiante y su contacto.
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.auth import Principal, Role
from app.domain.errors import ForbiddenError
from app.domain.models import JobOpportunity


@dataclass(frozen=True)
class ApplicantContact:
    name: str
    email: str
    phone: str | None = None


@dataclass(frozen=True)
class ApplicantSnapshot:
    """Lo que ve la empresa de quien se postuló (copia del perfil de profile-service)."""

    profile_id: str
    contact: ApplicantContact
    headline: str | None = None


@dataclass(frozen=True)
class Application:
    id: str
    job_id: str
    company_id: str
    student_id: str  # `sub` del JWT del estudiante (user_id de auth-service)
    applicant: ApplicantSnapshot
    applied_at: datetime
    updated_at: datetime


def require_student(principal: Principal) -> None:
    if principal.role is not Role.STUDENT:
        raise ForbiddenError("Sólo un estudiante puede postularse a una oferta")


def ensure_can_see_applicants(principal: Principal, job: JobOpportunity) -> None:
    """La empresa dueña, un admin o un servicio interno ven a los postulados."""
    if principal.sees_everything:
        return
    if principal.role is Role.COMPANY and principal.subject == job.company_id:
        return
    raise ForbiddenError(
        "Sólo la empresa dueña de la oferta ve a quienes se postularon",
        {"job_id": job.id},
    )
