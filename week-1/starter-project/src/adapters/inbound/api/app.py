"""Adaptador HTTP para el triaje y el resumen de incidentes."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.adapters.inbound.api.schemas import (
    ActiveIncidentsSummaryResponse,
    TriageRequest,
    TriageResponse,
)
from src.adapters.inbound.reference_time import parse_reference_time
from src.adapters.outbound.factory import create_incident_repository
from src.application.services import IncidentService, ValidationError


def create_app() -> FastAPI:
    app = FastAPI(title="IncidentOps Triage", version="1.0.0")
    triage_service = IncidentService()

    async def input_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    app.add_exception_handler(ValidationError, input_error_handler)
    app.add_exception_handler(ValueError, input_error_handler)

    @app.post("/api/v1/incidents/triage", response_model=TriageResponse, status_code=200)
    def triage(payload: TriageRequest) -> TriageResponse:
        result = triage_service.triage_incident(payload.incident_id, payload.raw_text)
        return TriageResponse.model_validate(result)

    @app.get(
        "/api/v1/incidents/summary",
        response_model=ActiveIncidentsSummaryResponse,
        status_code=200,
    )
    def summary(
        component: str | None = None, reference_time: str | None = None
    ) -> ActiveIncidentsSummaryResponse:
        instant = parse_reference_time(reference_time)
        service = IncidentService(create_incident_repository())
        result = service.get_active_incidents_summary(component, instant)
        return ActiveIncidentsSummaryResponse.model_validate(result)

    return app


app = create_app()
