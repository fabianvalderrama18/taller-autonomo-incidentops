"""Compatibilidad: las entidades viven en `src.domain.models`."""

from src.domain.models import (
    Incident,
    IncidentStatus,
    SLAEvaluation,
    SLARule,
    SeverityLevel,
    TriageResult,
)

__all__ = [
    "Incident",
    "IncidentStatus",
    "SLAEvaluation",
    "SLARule",
    "SeverityLevel",
    "TriageResult",
]
