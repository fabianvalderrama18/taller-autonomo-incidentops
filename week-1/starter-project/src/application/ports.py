"""Puertos secundarios de la capa de aplicación (ADR-003, ADR-004)."""

from datetime import datetime
from typing import Protocol, runtime_checkable

from src.domain.models import Incident, SeverityLevel


@runtime_checkable
class IncidentRepositoryPort(Protocol):
    """Persistencia de incidentes; el cálculo de SLA queda en el dominio.

    El puerto solo expone operaciones de almacenamiento y devuelve entidades de
    dominio. La conformidad es estructural: las implementaciones concretas no
    heredan de este ``Protocol`` para evitar falsos positivos en ``isinstance``.
    """

    def save_incident(self, incident: Incident) -> None: ...

    def get_incident(self, incident_id: str) -> Incident | None: ...

    def find_open_duplicates(
        self, component: str, severity: SeverityLevel, created_after: datetime | None = None
    ) -> list[Incident]: ...

    def list_active_incidents(self, component_filter: str | None = None) -> list[Incident]: ...

    def check_health(self) -> bool: ...
