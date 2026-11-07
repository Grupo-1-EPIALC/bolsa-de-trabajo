"""Repositorio PostgreSQL (SQLAlchemy 2.0) para el schema `jobs`.

Las ofertas de empresas dadas de baja pasan a `jobs_deleted` (auditoría) y salen de `jobs`.
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Any, cast

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    func,
    insert,
    select,
)
from sqlalchemy.engine import Engine

from app.domain.enums import JobStatus
from app.domain.models import JobOpportunity
from app.infrastructure.repositories.codec import job_from_document, job_to_document


def normalize_database_url(url: str) -> str:
    """SQLAlchemy necesita el driver explícito para psycopg 3."""
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


class SqlAlchemyJobRepository:
    def __init__(self, database_url: str, *, schema: str | None = "jobs") -> None:
        self._engine: Engine = create_engine(
            normalize_database_url(database_url),
            pool_pre_ping=True,
            future=True,
        )
        metadata = MetaData(schema=schema or None)
        self._table = Table(
            "jobs",
            metadata,
            Column("id", String(64), primary_key=True),
            Column("company_id", String(64), nullable=False, index=True),
            Column("status", String(16), nullable=False, index=True),
            Column("title", String(200), nullable=False),
            Column("published_at", DateTime(timezone=True), nullable=True, index=True),
            Column("version", Integer, nullable=False),
            Column("document", JSON, nullable=False),
            schema=schema or None,
        )
        self._archive = Table(
            "jobs_deleted",
            metadata,
            Column("id", String(64), primary_key=True),
            Column("company_id", String(64), nullable=False, index=True),
            Column("deleted_at", DateTime(timezone=True), nullable=False),
            Column("document", JSON, nullable=False),
            schema=schema or None,
        )
        metadata.create_all(self._engine)

    def add(self, job: JobOpportunity) -> None:
        with self._engine.begin() as connection:
            connection.execute(self._table.insert().values(**_row(job)))

    def update(self, job: JobOpportunity, *, expected_version: int) -> bool:
        """Guarda sólo si la fila sigue en `expected_version`; devuelve False si la superaron."""
        values = _row(job)
        values.pop("id")
        with self._engine.begin() as connection:
            result = connection.execute(
                self._table.update()
                .where(self._table.c.id == job.id, self._table.c.version == expected_version)
                .values(**values)
            )
        return bool(result.rowcount)

    def get(self, job_id: str) -> JobOpportunity | None:
        with self._engine.connect() as connection:
            document = connection.execute(
                select(self._table.c.document).where(self._table.c.id == job_id)
            ).scalar_one_or_none()
        if document is None:
            return None
        return job_from_document(cast(Mapping[str, Any], document))

    def list(
        self,
        *,
        status: JobStatus | None,
        company_id: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[JobOpportunity], int]:
        filters = []
        if status is not None:
            filters.append(self._table.c.status == status.value)
        if company_id is not None:
            filters.append(self._table.c.company_id == company_id)

        count_statement = select(func.count()).select_from(self._table)
        if filters:
            count_statement = count_statement.where(*filters)

        documents_statement = (
            select(self._table.c.document)
            .where(*filters)
            .order_by(self._table.c.published_at.desc(), self._table.c.id.asc())
            .offset(offset)
            .limit(limit)
        )

        with self._engine.connect() as connection:
            total = int(connection.execute(count_statement).scalar_one())
            documents = connection.execute(documents_statement).scalars().all()

        jobs = [job_from_document(cast(Mapping[str, Any], document)) for document in documents]
        return jobs, total

    def count(self) -> int:
        with self._engine.connect() as connection:
            return int(
                connection.execute(select(func.count()).select_from(self._table)).scalar_one()
            )

    def archive_company(self, company_id: str, deleted_at: datetime) -> int:
        table = self._table
        with self._engine.begin() as connection:
            rows = connection.execute(
                select(table.c.id, table.c.document)
                .where(table.c.company_id == company_id)
                .with_for_update()
            ).all()
            if not rows:
                return 0
            connection.execute(
                insert(self._archive),
                [
                    {
                        "id": row[0],
                        "company_id": company_id,
                        "deleted_at": deleted_at,
                        "document": row[1],
                    }
                    for row in rows
                ],
            )
            connection.execute(table.delete().where(table.c.company_id == company_id))
        return len(rows)

    def dispose(self) -> None:
        self._engine.dispose()


def _row(job: JobOpportunity) -> dict[str, Any]:
    return {
        "id": job.id,
        "company_id": job.company_id,
        "status": job.status.value,
        "title": job.title,
        "published_at": job.published_at,
        "version": job.version,
        "document": job_to_document(job),
    }
