"""Puertos (interfaces) de infraestructura. El dominio y la aplicación dependen sólo de esto."""

from typing import Any, Protocol

from app.domain.settings import AgentSettings

JsonDict = dict[str, Any]


class SettingsProvider(Protocol):
    async def get(self) -> AgentSettings: ...


class TextExtractor(Protocol):
    """Convierte el contenido binario de un formato de documento a texto plano."""

    format_name: str

    def extract(self, content: bytes) -> str: ...


class ProfileGateway(Protocol):
    async def get_profile(self, profile_id: str) -> JsonDict: ...

    async def list_profiles(self, skills: list[str], limit: int) -> list[JsonDict]: ...


class JobsGateway(Protocol):
    async def get_job(self, job_id: str) -> JsonDict: ...

    async def list_active_jobs(self, limit: int) -> list[JsonDict]: ...


class MatchingGateway(Protocol):
    async def compute_match(self, profile_id: str, job_id: str) -> JsonDict: ...

    async def missing_skills(self, profile_id: str, job_id: str) -> list[JsonDict]: ...

    async def rank_jobs_for_student(self, profile_id: str, limit: int | None) -> JsonDict:
        """Ofertas rankeadas por reglas. `limit=None` => cantidad configurada por el admin."""
        ...

    async def rank_candidates_for_job(self, job_id: str, limit: int | None) -> JsonDict:
        """Candidatos rankeados por reglas. `limit=None` => cantidad configurada por el admin."""
        ...


class CourseCatalog(Protocol):
    def search(self, skills: list[str], limit: int) -> list[JsonDict]: ...


class RecommendationStore(Protocol):
    async def save(self, recommendation: JsonDict) -> JsonDict: ...


class SchemaValidator(Protocol):
    def available(self) -> list[str]: ...

    def validate(self, schema_name: str, document: object) -> list[str]: ...


class RouterStateStore(Protocol):
    def load(self) -> JsonDict: ...

    def save(self, state: JsonDict) -> None: ...


class Clock(Protocol):
    def now_ms(self) -> int: ...

    def today(self) -> str: ...

    def iso_now(self) -> str: ...


class SkillRepository(Protocol):
    def list_skills(self) -> list[JsonDict]: ...

    def read_skill(
        self,
        skill_id: str,
        file_path: str = "SKILL.md",
        offset: int = 0,
        session_id: str = "default",
    ) -> JsonDict: ...
