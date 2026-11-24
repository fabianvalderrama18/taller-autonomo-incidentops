"""Casos de uso compartidos de IncidentOps (ADR-003, ADR-004)."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import uuid4

from src.application.ports import IncidentRepositoryPort
from src.domain.models import Incident, IncidentStatus, SeverityLevel, TriageResult
from src.domain.sla_calculator import evaluate_sla_status, normalize_datetime
from src.domain.triage_rules import classify_incident_report


class ValidationError(ValueError):
    """Entrada inválida detectada en el borde de la aplicación."""


@dataclass(frozen=True)
class ActiveIncidentDetail:
    """Vista de aplicación de un incidente activo, sin frameworks de entrega."""

    incident_id: str
    title: str
    component: str
    severity: SeverityLevel
    status: IncidentStatus
    elapsed_minutes: int
    requires_escalation: bool


@dataclass(frozen=True)
class ActiveIncidentsSummary:
    """Agregado devuelto por el caso de uso del resumen de activos."""

    total_active: int
    breached_count: int
    incidents: list[ActiveIncidentDetail]


class IncidentNotFoundError(LookupError):
    """El incidente solicitado no existe."""


class IncidentAlreadyExistsError(ValueError):
    """La creación no puede sobrescribir un incidente."""


class IncidentService:
    """Orquesta triaje y resumen sin persistencia propia ni reglas de negocio."""

    def __init__(self, repository: IncidentRepositoryPort | None = None) -> None:
        self._repository = repository

    def triage_incident(self, incident_id: str, raw_text: str) -> TriageResult:
        if not incident_id or not incident_id.strip():
            raise ValidationError("incident_id no puede estar vacío")
        if not raw_text or not raw_text.strip():
            raise ValidationError("raw_text no puede estar vacío")
        return classify_incident_report(incident_id, raw_text)

    def get_active_incidents_summary(
        self,
        component_filter: str | None = None,
        reference_time: datetime | None = None,
    ) -> ActiveIncidentsSummary:
        """Resume los activos filtrados usando el dominio para calcular el SLA."""
        if self._repository is None:
            raise ValidationError("Repositorio de incidentes no configurado")

        filtro = (
            component_filter.strip()
            if component_filter and component_filter.strip()
            else None
        )
        instant = reference_time if reference_time is not None else datetime.now()

        incidents = self._repository.list_active_incidents(filtro)
        details: list[ActiveIncidentDetail] = []
        breached_count = 0
        for incident in incidents:
            evaluation = evaluate_sla_status(incident, instant)
            if evaluation.is_breached:
                breached_count += 1
            details.append(
                ActiveIncidentDetail(
                    incident_id=incident.incident_id,
                    title=incident.title,
                    component=incident.component,
                    severity=incident.severity,
                    status=incident.status,
                    elapsed_minutes=evaluation.elapsed_minutes,
                    requires_escalation=evaluation.requires_escalation,
                )
            )
        return ActiveIncidentsSummary(
            total_active=len(details),
            breached_count=breached_count,
            incidents=details,
        )

    def create_incident(
        self,
        title: str,
        raw_text: str,
        incident_id: str | None = None,
        created_at: datetime | None = None,
        status: str = "OPEN",
    ) -> dict:
        if not title or not title.strip():
            raise ValidationError("title no puede estar vacío")
        if status not in ("OPEN", "IN_PROGRESS", "ESCALATION_REQUIRED", "RESOLVED"):
            raise ValidationError("status no válido")
        identifier = (
            incident_id if incident_id is not None else f"INC-{uuid4().hex[:8].upper()}"
        )
        classification = self.triage_incident(identifier, raw_text)
        if self._repository is None:
            raise ValidationError("Repositorio de incidentes no configurado")
        if self._repository.get_incident(identifier) is not None:
            raise IncidentAlreadyExistsError("incident_id ya registrado")
        instant = normalize_datetime(created_at or datetime.now(timezone.utc))
        duplicates = self._repository.find_open_duplicates(
            classification.duplicate_group_key, identifier
        )
        incident = Incident(
            identifier,
            title.strip(),
            classification.component,
            classification.severity,
            status,
            instant,
            recommended_team=classification.recommended_team,
            duplicate_group_key=classification.duplicate_group_key,
        )
        self._repository.save_incident(incident)
        return {
            **asdict(classification),
            **asdict(incident),
            "is_duplicate": bool(duplicates),
            "duplicate_of": sorted(item.incident_id for item in duplicates),
        }

    def evaluate_incident_sla(
        self, incident_id: str, reference_time: datetime | None = None
    ):
        if self._repository is None:
            raise ValidationError("Repositorio de incidentes no configurado")
        incident = self._repository.get_incident(incident_id)
        if incident is None:
            raise IncidentNotFoundError("Incidente no encontrado")
        instant = normalize_datetime(reference_time or datetime.now(timezone.utc))
        if instant < normalize_datetime(incident.created_at):
            raise ValidationError(
                "El tiempo de referencia no puede ser anterior a la creación"
            )
        return evaluate_sla_status(incident, instant)

    def check_health(self) -> bool:
        return self._repository is not None and self._repository.check_health()
