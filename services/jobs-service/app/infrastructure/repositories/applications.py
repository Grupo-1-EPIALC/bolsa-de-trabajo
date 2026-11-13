"""Repositorios de postulaciones (puerto `ApplicationRepository`): memoria y PostgreSQL."""

from collections.abc import Mapping
from datetime import UTC, datetime
from threading import Lock
from typing import Any, cast

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.exc import IntegrityError

from app.domain.applications import ApplicantContact, ApplicantSnapshot, Application
from app.infrastructure.repositories.sqlalchemy_jobs import normalize_database_url


def _newest_first(items: list[Application]) -> list[Application]:
    items.sort(key=lambda item: item.id)
    items.sort(key=lambda item: item.applied_at, reverse=True)
    return items


class InMemoryApplicationRepository:
    def __init__(self) -> None:
        self._lock = Lock()
        self._items: dict[tuple[str, str], Application] = {}

    def add(self, application: Application) -> bool:
        key = (application.job_id, application.student_id)
        with self._lock:
            if key in self._items:
                return False
            self._items[key] = application
            return True

    def update(self, application: Application) -> None:
        with self._lock:
            key = (application.job_id, application.student_id)
            if key in self._items:
                self._items[key] = application

    def get(self, job_id: str, student_id: str) -> Application | None:
        with self._lock:
            return self._items.get((job_id, student_id))

    def remove(self, job_id: str, student_id: str) -> bool:
        with self._lock:
            return self._items.pop((job_id, student_id), None) is not None

    def list_for_job(self, job_id: str) -> list[Application]:
        with self._lock:
            items = [item for item in self._items.values() if item.job_id == job_id]
        return _newest_first(items)

    def list_for_student(self, student_id: str) -> list[Application]:
        with self._lock:
            items = [item for item in self._items.values() if item.student_id == student_id]
        return _newest_first(items)

    def remove_student(self, student_id: str) -> int:
        return self._remove_where(lambda item: item.student_id == student_id)

    def remove_company(self, company_id: str) -> int:
        return self._remove_where(lambda item: item.company_id == company_id)

    def _remove_where(self, predicate: Any) -> int:
        with self._lock:
            keys = [key for key, item in self._items.items() if predicate(item)]
            for key in keys:
                del self._items[key]
        return len(keys)


class SqlAlchemyApplicationRepository:
    def __init__(self, database_url: str, *, schema: str | None = "jobs") -> None:
        self._engine = create_engine(
            normalize_database_url(database_url), pool_pre_ping=True, future=True
        )
        metadata = MetaData(schema=schema or None)
        self._table = Table(
            "applications",
            metadata,
            Column("id", String(64), primary_key=True),
            Column("job_id", String(64), nullable=False, index=True),
            Column("company_id", String(64), nullable=False, index=True),
            Column("student_id", String(64), nullable=False, index=True),
            Column("applied_at", DateTime(timezone=True), nullable=False),
            Column("updated_at", DateTime(timezone=True), nullable=False),
            Column("applicant", JSON, nullable=False),
            UniqueConstraint("job_id", "student_id", name="uq_applications_job_student"),
            schema=schema or None,
        )
        metadata.create_all(self._engine)

    def add(self, application: Application) -> bool:
        try:
            with self._engine.begin() as connection:
                connection.execute(self._table.insert().values(**_row(application)))
        except IntegrityError:
            return False  # ya estaba postulado (índice único job_id + student_id)
        return True

    def update(self, application: Application) -> None:
        table = self._table
        with self._engine.begin() as connection:
            connection.execute(
                table.update()
                .where(
                    table.c.job_id == application.job_id,
                    table.c.student_id == application.student_id,
                )
                .values(
                    updated_at=application.updated_at,
                    applicant=_applicant_document(application.applicant),
                )
            )

    def get(self, job_id: str, student_id: str) -> Application | None:
        table = self._table
        with self._engine.connect() as connection:
            row = connection.execute(
                select(table).where(table.c.job_id == job_id, table.c.student_id == student_id)
            ).first()
        return _from_row(row._mapping) if row is not None else None

    def remove(self, job_id: str, student_id: str) -> bool:
        table = self._table
        with self._engine.begin() as connection:
            result = connection.execute(
                table.delete().where(table.c.job_id == job_id, table.c.student_id == student_id)
            )
        return bool(result.rowcount)

    def list_for_job(self, job_id: str) -> list[Application]:
        return self._list(self._table.c.job_id == job_id)

    def list_for_student(self, student_id: str) -> list[Application]:
        return self._list(self._table.c.student_id == student_id)

    def remove_student(self, student_id: str) -> int:
        return self._delete(self._table.c.student_id == student_id)

    def remove_company(self, company_id: str) -> int:
        return self._delete(self._table.c.company_id == company_id)

    def dispose(self) -> None:
        self._engine.dispose()

    def _list(self, condition: Any) -> list[Application]:
        table = self._table
        with self._engine.connect() as connection:
            rows = connection.execute(
                select(table).where(condition).order_by(table.c.applied_at.desc(), table.c.id)
            ).all()
        return [_from_row(row._mapping) for row in rows]

    def _delete(self, condition: Any) -> int:
        with self._engine.begin() as connection:
            result = connection.execute(self._table.delete().where(condition))
        return int(result.rowcount or 0)


def _applicant_document(applicant: ApplicantSnapshot) -> dict[str, Any]:
    return {
        "profile_id": applicant.profile_id,
        "headline": applicant.headline,
        "contact": {
            "name": applicant.contact.name,
            "email": applicant.contact.email,
            "phone": applicant.contact.phone,
        },
    }


def _row(application: Application) -> dict[str, Any]:
    return {
        "id": application.id,
        "job_id": application.job_id,
        "company_id": application.company_id,
        "student_id": application.student_id,
        "applied_at": application.applied_at,
        "updated_at": application.updated_at,
        "applicant": _applicant_document(application.applicant),
    }


def _utc(value: datetime) -> datetime:
    # SQLite (tests) devuelve fechas sin zona horaria aunque la columna la declare.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _from_row(row: Mapping[Any, Any]) -> Application:
    applicant = cast(Mapping[str, Any], row["applicant"])
    contact = cast(Mapping[str, Any], applicant.get("contact") or {})
    return Application(
        id=str(row["id"]),
        job_id=str(row["job_id"]),
        company_id=str(row["company_id"]),
        student_id=str(row["student_id"]),
        applied_at=_utc(row["applied_at"]),
        updated_at=_utc(row["updated_at"]),
        applicant=ApplicantSnapshot(
            profile_id=str(applicant.get("profile_id", "")),
            headline=applicant.get("headline"),
            contact=ApplicantContact(
                name=str(contact.get("name", "")),
                email=str(contact.get("email", "")),
                phone=contact.get("phone"),
            ),
        ),
    )
