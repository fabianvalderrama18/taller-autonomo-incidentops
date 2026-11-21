"""Fábrica del adaptador de persistencia (ADR-001, ADR-003, ADR-004)."""

import os

from src.adapters.outbound.sqlite_repository import SQLiteIncidentRepository
from src.application.ports import IncidentRepositoryPort


def create_incident_repository(database_url: str | None = None) -> IncidentRepositoryPort:
    """Construye el repositorio resolviendo `DATABASE_URL` en el borde.

    H002 consulta incidentes activos; H001 permanece stateless. La factory es el
    único punto donde los adaptadores primarios obtienen persistencia concreta.
    """
    url = database_url or os.getenv("DATABASE_URL", "sqlite:///:memory:")
    db_path = url.removeprefix("sqlite:///") if url.startswith("sqlite:///") else url
    return SQLiteIncidentRepository(db_path=db_path)
