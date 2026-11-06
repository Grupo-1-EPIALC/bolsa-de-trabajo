"""Repositorio PostgreSQL (SQLAlchemy 2.0) en el schema `profile`.

Una fila por perfil: columnas indexadas para buscar y el documento JSON completo.
"""

from collections.abc import Mapping
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
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.sql.elements import ColumnElement

from app.domain.profile import StudentProfile
from app.domain.serialization import from_plain, to_plain


def normalize_database_url(url: str) -> str:
    """SQLAlchemy necesita el driver explícito para psycopg 3."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


class SqlAlchemyProfileRepository:
    def __init__(self, database_url: str, *, schema: str | None = "profile") -> None:
        self._engine: Engine = create_engine(
            normalize_database_url(database_url), pool_pre_ping=True, future=True
        )
        metadata = MetaData(schema=schema or None)
        self._table = Table(
            "profiles",
            metadata,
            Column("id", String(64), primary_key=True),
            Column("user_id", String(64), nullable=False, unique=True, index=True),
            Column("status", String(16), nullable=False, index=True),
            Column("updated_at", DateTime(timezone=True), nullable=False),
            Column("version", Integer, nullable=False),
            Column("document", JSON, nullable=False),
            schema=schema or None,
        )
        metadata.create_all(self._engine)

    def add(self, profile: StudentProfile) -> None:
        with self._engine.begin() as conn:
            conn.execute(self._table.insert().values(**_row(profile)))

    def update(self, profile: StudentProfile) -> None:
        values = _row(profile)
        values.pop("id")
        with self._engine.begin() as conn:
            conn.execute(
                self._table.update().where(self._table.c.id == profile.id).values(**values)
            )

    def get(self, profile_id: str) -> StudentProfile | None:
        return self._one(self._table.c.id == profile_id)

    def get_by_user(self, user_id: str) -> StudentProfile | None:
        return self._one(self._table.c.user_id == user_id)

    def list(self, *, offset: int, limit: int) -> tuple[list[StudentProfile], int]:
        statement = (
            select(self._table.c.document).order_by(self._table.c.id).offset(offset).limit(limit)
        )
        with self._engine.connect() as conn:
            total = int(conn.execute(select(func.count()).select_from(self._table)).scalar_one())
            documents = conn.execute(statement).scalars().all()
        return [_decode(d) for d in documents], total

    def count(self) -> int:
        with self._engine.connect() as conn:
            return int(conn.execute(select(func.count()).select_from(self._table)).scalar_one())

    def dispose(self) -> None:
        self._engine.dispose()

    def _one(self, condition: ColumnElement[bool]) -> StudentProfile | None:
        with self._engine.connect() as conn:
            document = conn.execute(
                select(self._table.c.document).where(condition)
            ).scalar_one_or_none()
        return None if document is None else _decode(document)


def _decode(document: Any) -> StudentProfile:
    return from_plain(StudentProfile, cast(Mapping[str, Any], document))


def _row(profile: StudentProfile) -> dict[str, Any]:
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "status": profile.status.value,
        "updated_at": profile.updated_at,
        "version": profile.version,
        "document": to_plain(profile),
    }
