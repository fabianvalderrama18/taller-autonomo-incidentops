"""Adaptador HTTP para el triaje y el resumen de incidentes."""

from contextlib import asynccontextmanager, contextmanager
from threading import RLock
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.adapters.inbound.api.schemas import (
    ActiveIncidentsSummaryResponse,
    TriageRequest,
    TriageResponse,
    CreateIncidentRequest,
    IncidentCreatedResponse,
    SLAEvaluationResponse,
    HealthResponse,
)
from src.adapters.inbound.reference_time import (
    parse_reference_time,
    parse_lifecycle_time,
)
from src.adapters.outbound.factory import create_incident_repository, repository_scope
from src.application.services import (
    IncidentService,
    ValidationError,
    IncidentNotFoundError,
    IncidentAlreadyExistsError,
)


def create_app() -> FastAPI:
    lock = RLock()
    memory_repository = None

    @asynccontextmanager
    async def lifespan(app):
        yield
        if memory_repository is not None:
            memory_repository.close()

    app = FastAPI(title="IncidentOps", version="2.0.0", lifespan=lifespan)

    @contextmanager
    def service_scope():
        nonlocal memory_repository
        # Serializa el uso de la conexión en memoria; se conserva entre requests.
        with lock:
            if os.getenv("DATABASE_URL", "sqlite:///:memory:") == "sqlite:///:memory:":
                if memory_repository is None:
                    memory_repository = create_incident_repository()
                yield IncidentService(memory_repository)
            else:
                with repository_scope() as repository:
                    yield IncidentService(repository)

    triage_service = IncidentService()

    async def input_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    async def not_found(_request, exc):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    async def conflict(_request, exc):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    app.add_exception_handler(IncidentNotFoundError, not_found)
    app.add_exception_handler(IncidentAlreadyExistsError, conflict)
    app.add_exception_handler(ValidationError, input_error_handler)
    app.add_exception_handler(ValueError, input_error_handler)

    @app.post(
        "/api/v1/incidents/triage", response_model=TriageResponse, status_code=200
    )
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
        with service_scope() as service:
            result = service.get_active_incidents_summary(component, instant)
        return ActiveIncidentsSummaryResponse.model_validate(result)

    @app.post(
        "/api/v1/incidents", response_model=IncidentCreatedResponse, status_code=201
    )
    def create(payload: CreateIncidentRequest):
        with service_scope() as service:
            return service.create_incident(
                payload.title,
                payload.raw_text,
                payload.incident_id,
                parse_lifecycle_time(payload.created_at),
                payload.status,
            )

    @app.get(
        "/api/v1/incidents/{incident_id}/sla", response_model=SLAEvaluationResponse
    )
    def sla(incident_id: str, reference_time: str | None = None):
        with service_scope() as service:
            return service.evaluate_incident_sla(
                incident_id, parse_lifecycle_time(reference_time)
            )

    @app.get("/health", response_model=HealthResponse)
    def health():
        try:
            with service_scope() as service:
                healthy = service.check_health()
        except Exception:
            healthy = False
        return JSONResponse(
            status_code=200 if healthy else 503,
            content={
                "status": "ok" if healthy else "error",
                "database": "connected" if healthy else "unavailable",
            },
        )

    return app


app = create_app()
