"""Repositorios PostgreSQL del perfil de empresa (`company_profiles`) y del logo
(`company_logos`, binario ≤ 1 MB) en el schema `profile`.
Los perfiles de cuentas borradas pasan a `company_profiles_deleted` (auditoría).
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Any, cast

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Table,
    create_engine,
    func,
    insert,
    select,
)
from sqlalchemy.engine import Engine

from app.domain.company import CompanyProfile
from app.domain.ports import StoredLogo
from app.domain.serialization import from_plain, to_plain
from app.infrastructure.repositories.sqlalchemy_repo import normalize_database_url


def _engine(database_url: str) -> Engine:
    return create_engine(normalize_database_url(database_url), pool_pre_ping=True, future=True)


class SqlAlchemyCompanyProfileRepository:
    def __init__(self, database_url: str, *, schema: str | None = "profile") -> None:
        self._engine = _engine(database_url)
        metadata = MetaData(schema=schema or None)
        self._table = Table(
            "company_profiles",
            metadata,
            Column("company_id", String(64), primary_key=True),
            Column("id", String(64), nullable=False, unique=True),
            Column("status", String(16), nullable=False, index=True),
            Column("updated_at", DateTime(timezone=True), nullable=False),
            Column("version", Integer, nullable=False),
            Column("document", JSON, nullable=False),
            schema=schema or None,
        )
        self._archive = Table(
            "company_profiles_deleted",
            metadata,
            Column("company_id", String(64), primary_key=True),
            Column("id", String(64), nullable=False),
            Column("deleted_at", DateTime(timezone=True), nullable=False),
            Column("document", JSON, nullable=False),
            schema=schema or None,
        )
        metadata.create_all(self._engine)

    def add(self, profile: CompanyProfile) -> None:
        with self._engine.begin() as conn:
            conn.execute(self._table.insert().values(**_row(profile)))

    def update(self, profile: CompanyProfile) -> None:
        values = _row(profile)
        values.pop("company_id")
        with self._engine.begin() as conn:
            conn.execute(
                self._table.update()
                .where(self._table.c.company_id == profile.company_id)
                .values(**values)
            )

    def get_by_company(self, company_id: str) -> CompanyProfile | None:
        with self._engine.connect() as conn:
            document = conn.execute(
                select(self._table.c.document).where(self._table.c.company_id == company_id)
            ).scalar_one_or_none()
        return None if document is None else _decode(document)

    def list(self, *, offset: int, limit: int) -> tuple[list[CompanyProfile], int]:
        statement = (
            select(self._table.c.document).order_by(self._table.c.id).offset(offset).limit(limit)
        )
        with self._engine.connect() as conn:
            total = int(conn.execute(select(func.count()).select_from(self._table)).scalar_one())
            documents = conn.execute(statement).scalars().all()
        return [_decode(d) for d in documents], total

    def archive(self, company_id: str, deleted_at: datetime) -> bool:
        table = self._table
        with self._engine.begin() as conn:
            row = conn.execute(
                select(table.c.id, table.c.document)
                .where(table.c.company_id == company_id)
                .with_for_update()
            ).one_or_none()
            if row is None:
                return False
            conn.execute(
                insert(self._archive).values(
                    company_id=company_id, id=row[0], deleted_at=deleted_at, document=row[1]
                )
            )
            conn.execute(table.delete().where(table.c.company_id == company_id))
        return True

    def dispose(self) -> None:
        self._engine.dispose()


class SqlAlchemyLogoStore:
    def __init__(self, database_url: str, *, schema: str | None = "profile") -> None:
        self._engine = _engine(database_url)
        metadata = MetaData(schema=schema or None)
        self._table = Table(
            "company_logos",
            metadata,
            Column("company_id", String(64), primary_key=True),
            Column("mime_type", String(32), nullable=False),
            Column("content", LargeBinary, nullable=False),
            schema=schema or None,
        )
        metadata.create_all(self._engine)

    def save(self, company_id: str, logo: StoredLogo) -> None:
        with self._engine.begin() as conn:
            conn.execute(self._table.delete().where(self._table.c.company_id == company_id))
            conn.execute(
                self._table.insert().values(
                    company_id=company_id, mime_type=logo.mime_type, content=logo.content
                )
            )

    def get(self, company_id: str) -> StoredLogo | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                select(self._table.c.mime_type, self._table.c.content).where(
                    self._table.c.company_id == company_id
                )
            ).one_or_none()
        return None if row is None else StoredLogo(str(row[0]), bytes(row[1]))

    def delete(self, company_id: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(self._table.delete().where(self._table.c.company_id == company_id))

    def dispose(self) -> None:
        self._engine.dispose()


def _decode(document: Any) -> CompanyProfile:
    return from_plain(CompanyProfile, cast(Mapping[str, Any], document))


def _row(profile: CompanyProfile) -> dict[str, Any]:
    return {
        "company_id": profile.company_id,
        "id": profile.id,
        "status": profile.status.value,
        "updated_at": profile.updated_at,
        "version": profile.version,
        "document": to_plain(profile),
    }
