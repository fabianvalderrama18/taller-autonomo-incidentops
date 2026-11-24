"""Esquemas Pydantic v2 del adaptador HTTP."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.domain.models import IncidentStatus, SeverityLevel


class TriageRequest(BaseModel):
    incident_id: str
    raw_text: str


class TriageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    incident_id: str
    severity: SeverityLevel
    component: str
    rationale: str
    recommended_team: str
    duplicate_group_key: str
    consistency_ratio: float


class ActiveIncidentItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    incident_id: str
    title: str
    component: str
    severity: SeverityLevel
    status: IncidentStatus
    elapsed_minutes: int
    requires_escalation: bool


class ActiveIncidentsSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_active: int
    breached_count: int
    incidents: list[ActiveIncidentItem]


class CreateIncidentRequest(BaseModel):
    title: str
    raw_text: str
    incident_id: str | None = None
    created_at: str | None = None
    status: str = "OPEN"


class IncidentCreatedResponse(TriageResponse):
    title: str
    status: IncidentStatus
    created_at: datetime
    resolved_at: datetime | None = None
    is_duplicate: bool
    duplicate_of: list[str]


class SLAEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    incident_id: str
    severity: SeverityLevel
    elapsed_minutes: int
    allowed_minutes: int
    remaining_minutes: int
    is_breached: bool
    requires_escalation: bool


class HealthResponse(BaseModel):
    status: str
    database: str
