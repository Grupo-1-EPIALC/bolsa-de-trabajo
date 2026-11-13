"""Persistencia SQLAlchemy para recomendaciones, pedidos y configuración de matching."""

from collections.abc import Mapping
from typing import Any, cast

from sqlalchemy import (
    JSON,
    Column,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    select,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.domain.recommendations import (
    AiMetadata,
    AiRecommendation,
    RecommendationMode,
    RecommendationRequest,
    RequestStatus,
)
from app.domain.settings import RecommendationSettings


def normalize_database_url(url: str) -> str:
    """Agrega el driver psycopg 3 a las URL PostgreSQL del proyecto."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


class SqlAlchemyMatchingDatabase:
    """Engine y tablas del schema de matching, compartidos por sus repositorios."""

    def __init__(self, database_url: str, *, schema: str | None = "matching") -> None:
        self._engine: Engine = create_engine(
            normalize_database_url(database_url), pool_pre_ping=True, future=True
        )
        metadata = MetaData(schema=schema or None)

        self.recommendations = Table(
            "recommendations",
            metadata,
            Column("row_id", Integer, primary_key=True, autoincrement=True),
            Column("id", String(64), nullable=False, unique=True),
            Column("mode", String(16), nullable=False),
            Column("profile_id", String(64), nullable=False),
            Column("job_id", String(64), nullable=False),
            Column("document", JSON, nullable=False),
            schema=schema or None,
        )
        Index(
            "ix_matching_recommendations_profile",
            self.recommendations.c.mode,
            self.recommendations.c.profile_id,
            self.recommendations.c.row_id,
        )
        Index(
            "ix_matching_recommendations_job",
            self.recommendations.c.mode,
            self.recommendations.c.job_id,
            self.recommendations.c.row_id,
        )

        self.requests = Table(
            "recommendation_requests",
            metadata,
            Column("row_id", Integer, primary_key=True, autoincrement=True),
            Column("id", String(64), nullable=False, unique=True),
            Column("mode", String(16), nullable=False),
            Column("subject_id", String(64), nullable=False),
            Column("job_id", String(64), nullable=False),
            Column("document", JSON, nullable=False),
            schema=schema or None,
        )
        Index(
            "ix_matching_requests_subject",
            self.requests.c.mode,
            self.requests.c.subject_id,
            self.requests.c.row_id,
        )

        self.settings = Table(
            "recommendation_settings",
            metadata,
            Column("key", String(32), primary_key=True),
            Column("student_jobs_limit", Integer, nullable=False),
            Column("company_candidates_limit", Integer, nullable=False),
            Column("updated_at", String(40), nullable=False),
            Column("updated_by", String(64), nullable=False),
            schema=schema or None,
        )
        metadata.create_all(self._engine)

    @property
    def engine(self) -> Engine:
        return self._engine

    def dispose(self) -> None:
        self._engine.dispose()


class SqlAlchemyRecommendationRepository:
    def __init__(self, database: SqlAlchemyMatchingDatabase) -> None:
        self._database = database
        self._table = database.recommendations

    def save(self, recommendation: AiRecommendation) -> AiRecommendation:
        self.save_many([recommendation])
        return recommendation

    def save_many(self, recommendations: list[AiRecommendation]) -> list[AiRecommendation]:
        if not recommendations:
            return []
        with self._database.engine.begin() as connection:
            connection.execute(
                self._table.insert(),
                [_recommendation_row(recommendation) for recommendation in recommendations],
            )
        return list(recommendations)

    def latest_for_profile(self, profile_id: str) -> list[AiRecommendation]:
        return self._latest(RecommendationMode.STUDENT, "profile_id", profile_id, "job_id")

    def latest_for_job(self, job_id: str) -> list[AiRecommendation]:
        return self._latest(RecommendationMode.COMPANY, "job_id", job_id, "profile_id")

    def latest_training(self, profile_id: str) -> AiRecommendation | None:
        recommendations = self._latest(
            RecommendationMode.TRAINING, "profile_id", profile_id, "job_id"
        )
        return next((item for item in recommendations if item.job_id == "general"), None)

    def _latest(
        self, mode: RecommendationMode, key_column: str, key: str, group_column: str
    ) -> list[AiRecommendation]:
        statement = (
            select(self._table.c.document)
            .where(
                self._table.c.mode == mode.value,
                getattr(self._table.c, key_column) == key,
            )
            .order_by(self._table.c.row_id.desc())
        )
        with self._database.engine.connect() as connection:
            documents = connection.execute(statement).scalars().all()

        latest: list[AiRecommendation] = []
        seen: set[str] = set()
        for document in documents:
            recommendation = _recommendation_from_document(cast(Mapping[str, Any], document))
            group_key = str(getattr(recommendation, group_column))
            if group_key not in seen:
                latest.append(recommendation)
                seen.add(group_key)
        return latest


class SqlAlchemyRecommendationRequestRepository:
    def __init__(self, database: SqlAlchemyMatchingDatabase) -> None:
        self._database = database
        self._table = database.requests

    def save(self, request: RecommendationRequest) -> RecommendationRequest:
        values = _request_row(request)
        with self._database.engine.begin() as connection:
            result = connection.execute(
                update(self._table).where(self._table.c.id == request.id).values(**values)
            )
            if result.rowcount == 0:
                connection.execute(self._table.insert().values(**values))
        return request

    def get(self, request_id: str) -> RecommendationRequest | None:
        statement = select(self._table.c.document).where(self._table.c.id == request_id)
        with self._database.engine.connect() as connection:
            document = connection.execute(statement).scalar_one_or_none()
        if document is None:
            return None
        return _request_from_document(cast(Mapping[str, Any], document))

    def latest_for(
        self, mode: str, subject_id: str, job_id: str = ""
    ) -> RecommendationRequest | None:
        statement = (
            select(self._table.c.document)
            .where(self._table.c.mode == mode, self._table.c.subject_id == subject_id)
            .order_by(self._table.c.row_id.desc())
            .limit(1)
        )
        if job_id:
            statement = statement.where(self._table.c.job_id == job_id)
        with self._database.engine.connect() as connection:
            document = connection.execute(statement).scalar_one_or_none()
        if document is None:
            return None
        return _request_from_document(cast(Mapping[str, Any], document))


class SqlAlchemySettingsRepository:
    def __init__(
        self, database: SqlAlchemyMatchingDatabase, initial: RecommendationSettings
    ) -> None:
        self._database = database
        self._table = database.settings
        self._ensure_default(initial)

    def get(self) -> RecommendationSettings:
        statement = select(self._table).where(self._table.c.key == "default")
        with self._database.engine.connect() as connection:
            row = connection.execute(statement).mappings().one_or_none()
        if row is None:
            raise RuntimeError("No se encontró la configuración persistida de matching")
        return RecommendationSettings(
            student_jobs_limit=int(row["student_jobs_limit"]),
            company_candidates_limit=int(row["company_candidates_limit"]),
            updated_at=str(row["updated_at"]),
            updated_by=str(row["updated_by"]),
        )

    def save(self, settings: RecommendationSettings) -> RecommendationSettings:
        statement = (
            update(self._table)
            .where(self._table.c.key == "default")
            .values(
                student_jobs_limit=settings.student_jobs_limit,
                company_candidates_limit=settings.company_candidates_limit,
                updated_at=settings.updated_at,
                updated_by=settings.updated_by,
            )
        )
        with self._database.engine.begin() as connection:
            result = connection.execute(statement)
        if result.rowcount != 1:
            raise RuntimeError("No se pudo actualizar la configuración persistida de matching")
        return settings

    def _ensure_default(self, initial: RecommendationSettings) -> None:
        exists = self._has_default()
        if exists:
            return
        try:
            with self._database.engine.begin() as connection:
                connection.execute(
                    self._table.insert().values(
                        key="default",
                        student_jobs_limit=initial.student_jobs_limit,
                        company_candidates_limit=initial.company_candidates_limit,
                        updated_at=initial.updated_at,
                        updated_by=initial.updated_by,
                    )
                )
        except IntegrityError:
            if not self._has_default():
                raise

    def _has_default(self) -> bool:
        statement = select(self._table.c.key).where(self._table.c.key == "default")
        with self._database.engine.connect() as connection:
            return connection.execute(statement).scalar_one_or_none() is not None


def _recommendation_row(recommendation: AiRecommendation) -> dict[str, Any]:
    return {
        "id": recommendation.id,
        "mode": recommendation.mode.value,
        "profile_id": recommendation.profile_id,
        "job_id": recommendation.job_id,
        "document": {
            "id": recommendation.id,
            "mode": recommendation.mode.value,
            "profile_id": recommendation.profile_id,
            "job_id": recommendation.job_id,
            "content": dict(recommendation.content),
            "items": [dict(item) for item in recommendation.items],
            "summary": recommendation.summary,
            "request_id": recommendation.request_id,
            "created_at": recommendation.created_at,
            "metadata": {
                "model": recommendation.metadata.model,
                "prompt_version": recommendation.metadata.prompt_version,
                "generated_at": recommendation.metadata.generated_at,
                "disclaimer": recommendation.metadata.disclaimer,
                "verified": recommendation.metadata.verified,
            },
        },
    }


def _recommendation_from_document(document: Mapping[str, Any]) -> AiRecommendation:
    metadata = cast(Mapping[str, Any], document["metadata"])
    return AiRecommendation(
        id=str(document["id"]),
        mode=RecommendationMode(str(document["mode"])),
        profile_id=str(document["profile_id"]),
        job_id=str(document["job_id"]),
        content=cast(Mapping[str, object], document["content"]),
        items=tuple(cast(Mapping[str, object], item) for item in document["items"]),
        summary=str(document["summary"]),
        request_id=str(document["request_id"]),
        created_at=str(document["created_at"]),
        metadata=AiMetadata(
            model=str(metadata["model"]),
            prompt_version=str(metadata["prompt_version"]),
            generated_at=str(metadata["generated_at"]),
            disclaimer=str(metadata["disclaimer"]),
            verified=bool(metadata["verified"]),
        ),
    )


def _request_row(request: RecommendationRequest) -> dict[str, Any]:
    return {
        "id": request.id,
        "mode": request.mode.value,
        "subject_id": request.subject_id,
        "job_id": request.job_id,
        "document": {
            "id": request.id,
            "mode": request.mode.value,
            "subject_id": request.subject_id,
            "job_id": request.job_id,
            "status": request.status.value,
            "created_at": request.created_at,
            "updated_at": request.updated_at,
            "error": dict(request.error),
        },
    }


def _request_from_document(document: Mapping[str, Any]) -> RecommendationRequest:
    return RecommendationRequest(
        id=str(document["id"]),
        mode=RecommendationMode(str(document["mode"])),
        subject_id=str(document["subject_id"]),
        job_id=str(document["job_id"]),
        status=RequestStatus(str(document["status"])),
        created_at=str(document["created_at"]),
        updated_at=str(document["updated_at"]),
        error=cast(Mapping[str, object], document["error"]),
    )
