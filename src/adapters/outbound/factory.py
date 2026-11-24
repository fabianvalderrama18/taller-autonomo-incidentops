"""Selección y ciclo de conexión de persistencia en el borde."""

import os
from contextlib import contextmanager

from src.adapters.outbound.postgres_repository import PostgresIncidentRepository
from src.adapters.outbound.sqlite_repository import SQLiteIncidentRepository
from src.application.ports import IncidentRepositoryPort


def create_repository(database_url: str | None = None) -> IncidentRepositoryPort:
    url = (
        database_url
        if database_url is not None
        else os.getenv("DATABASE_URL", "sqlite:///:memory:")
    )
    if url.startswith("postgresql://"):
        return PostgresIncidentRepository(url)
    if url.startswith("sqlite:///"):
        return SQLiteIncidentRepository(url.removeprefix("sqlite:///"))
    raise ValueError("DATABASE_URL debe usar sqlite:/// o postgresql://")


create_incident_repository = create_repository


@contextmanager
def repository_scope():
    repository = create_repository()
    try:
        yield repository
    finally:
        close = getattr(repository, "close", None)
        if close:
            close()
