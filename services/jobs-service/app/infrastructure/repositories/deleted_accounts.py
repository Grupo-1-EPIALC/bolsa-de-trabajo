"""Registro de cuentas dadas de baja en auth-service (puerto `DeletedAccounts`).

Sirve para rechazar el access token que todavía no venció de una cuenta borrada y para que
el seed de demo no vuelva a cargar ofertas de una empresa borrada.
"""

from datetime import datetime
from threading import Lock

from sqlalchemy import Column, DateTime, MetaData, String, Table, create_engine, select
from sqlalchemy.exc import IntegrityError

from app.infrastructure.repositories.sqlalchemy_jobs import normalize_database_url


class InMemoryDeletedAccounts:
    def __init__(self) -> None:
        self._lock = Lock()
        self._items: dict[str, tuple[str, datetime]] = {}

    def mark(self, user_id: str, role: str, deleted_at: datetime) -> bool:
        with self._lock:
            if user_id in self._items:
                return False
            self._items[user_id] = (role, deleted_at)
            return True

    def contains(self, user_id: str) -> bool:
        with self._lock:
            return user_id in self._items


class SqlAlchemyDeletedAccounts:
    def __init__(self, database_url: str, *, schema: str | None = "jobs") -> None:
        self._engine = create_engine(
            normalize_database_url(database_url), pool_pre_ping=True, future=True
        )
        metadata = MetaData(schema=schema or None)
        self._table = Table(
            "deleted_accounts",
            metadata,
            Column("user_id", String(64), primary_key=True),
            Column("role", String(16), nullable=False),
            Column("deleted_at", DateTime(timezone=True), nullable=False),
            schema=schema or None,
        )
        metadata.create_all(self._engine)

    def mark(self, user_id: str, role: str, deleted_at: datetime) -> bool:
        try:
            with self._engine.begin() as connection:
                connection.execute(
                    self._table.insert().values(user_id=user_id, role=role, deleted_at=deleted_at)
                )
        except IntegrityError:
            return False  # ya estaba registrada: evento repetido
        return True

    def contains(self, user_id: str) -> bool:
        with self._engine.connect() as connection:
            found = connection.execute(
                select(self._table.c.user_id).where(self._table.c.user_id == user_id)
            ).first()
        return found is not None

    def dispose(self) -> None:
        self._engine.dispose()
