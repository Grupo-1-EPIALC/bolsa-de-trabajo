"""Reglas de acceso por rol y dueño del recurso.

- `service` (n8n / mcp-tools) y `admin`: acceso completo.
- `student`: sólo a los matches y recomendaciones de su propio perfil (`profile.user_id == sub`).
- `company`: sólo a los de sus propias ofertas (`job.company_id == sub`).

Se responde 404 (no 403) cuando el recurso es de otro usuario, para no revelar qué ids existen.
"""

from app.application.matching_service import MatchingService
from app.domain.auth import Principal, Role
from app.domain.errors import ForbiddenError, NotFoundError
from app.domain.models import JobOpportunity, StudentProfile
from app.domain.recommendations import RecommendationMode


class AccessPolicy:
    def __init__(self, matching: MatchingService) -> None:
        self._matching = matching

    @staticmethod
    def require_service(principal: Principal) -> None:
        if not principal.is_service:
            raise ForbiddenError("Endpoint interno: sólo para servicios (n8n / mcp-tools)")

    def student_profile(self, principal: Principal, profile_id: str) -> StudentProfile:
        """Perfil al que puede acceder `principal` como estudiante."""
        profile = self._matching.load_profile(profile_id)
        if principal.sees_everything:
            return profile
        if (
            principal.role is Role.STUDENT
            and profile.user_id
            and profile.user_id == principal.subject
        ):
            return profile
        if principal.role is Role.COMPANY:
            raise ForbiddenError("Una empresa no puede ver las recomendaciones de un estudiante")
        raise _hidden("Perfil", profile_id)

    def company_job(self, principal: Principal, job_id: str) -> JobOpportunity:
        """Oferta a la que puede acceder `principal` como empresa dueña."""
        job = self._matching.load_job(job_id)
        if principal.sees_everything:
            return job
        if (
            principal.role is Role.COMPANY
            and job.company_id
            and job.company_id == principal.subject
        ):
            return job
        if principal.role is Role.STUDENT:
            raise ForbiddenError("Un estudiante no puede ver los candidatos de una oferta")
        raise _hidden("Oferta", job_id)

    def subject(self, principal: Principal, mode: object, subject_id: str) -> None:
        """Valida el acceso al sujeto de un pedido de análisis (`student` o `company`)."""
        if str(mode) == RecommendationMode.COMPANY.value:
            self.company_job(principal, subject_id)
        else:
            self.student_profile(principal, subject_id)

    def match(self, principal: Principal, profile_id: str, job_id: str) -> None:
        """Un match puntual lo ve el estudiante del perfil o la empresa de la oferta."""
        if principal.sees_everything:
            return
        if principal.role is Role.STUDENT:
            self.student_profile(principal, profile_id)
            self._matching.load_job(job_id)  # cualquier oferta activa es visible para postularse
            return
        if principal.role is Role.COMPANY:
            self.company_job(principal, job_id)
            self._matching.load_profile(profile_id)
            return
        raise ForbiddenError("Rol sin acceso a matches")


def _hidden(kind: str, resource_id: str) -> NotFoundError:
    return NotFoundError(f"{kind} '{resource_id}' no encontrado", {"id": resource_id})
