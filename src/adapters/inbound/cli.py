"""Adaptador CLI para el triaje y el resumen de incidentes."""

import json
from dataclasses import asdict
from typing import Annotated

import typer

from src.adapters.inbound.api.schemas import (
    ActiveIncidentsSummaryResponse,
    IncidentCreatedResponse,
    SLAEvaluationResponse,
)
from src.adapters.inbound.reference_time import (
    parse_reference_time,
    parse_lifecycle_time,
)
from src.adapters.outbound.factory import repository_scope
from src.application.services import (
    IncidentService,
    ValidationError,
    IncidentNotFoundError,
)

app = typer.Typer(add_completion=False)
triage_service = IncidentService()


@app.callback()
def main() -> None:
    """IncidentOps CLI."""


@app.command("triage")
def triage(
    incident_id: Annotated[str, typer.Option("--incident-id")],
    raw_text: Annotated[str, typer.Option("--raw-text")],
) -> None:
    try:
        result = triage_service.triage_incident(incident_id, raw_text)
    except ValidationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(json.dumps(asdict(result), ensure_ascii=False))


@app.command("summary")
def summary(
    component: Annotated[str | None, typer.Option("--component")] = None,
    reference_time: Annotated[str | None, typer.Option("--reference-time")] = None,
) -> None:
    try:
        instant = parse_reference_time(reference_time)
        with repository_scope() as repository:
            result = IncidentService(repository).get_active_incidents_summary(
                component, instant
            )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(ActiveIncidentsSummaryResponse.model_validate(result).model_dump_json())


@app.command("create")
def create(
    title: Annotated[str, typer.Option("--title")],
    raw_text: Annotated[str, typer.Option("--raw-text")],
    incident_id: Annotated[str | None, typer.Option("--incident-id")] = None,
    created_at: Annotated[str | None, typer.Option("--created-at")] = None,
    status: Annotated[str, typer.Option("--status")] = "OPEN",
):
    try:
        with repository_scope() as repository:
            result = IncidentService(repository).create_incident(
                title, raw_text, incident_id, parse_lifecycle_time(created_at), status
            )
        typer.echo(IncidentCreatedResponse.model_validate(result).model_dump_json())
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


@app.command("sla")
def sla(
    incident_id: Annotated[str, typer.Option("--incident-id")],
    reference_time: Annotated[str | None, typer.Option("--reference-time")] = None,
):
    try:
        with repository_scope() as repository:
            result = IncidentService(repository).evaluate_incident_sla(
                incident_id, parse_lifecycle_time(reference_time)
            )
        typer.echo(SLAEvaluationResponse.model_validate(result).model_dump_json())
    except (ValueError, IncidentNotFoundError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


@app.command("health")
def health():
    try:
        with repository_scope() as repository:
            healthy = IncidentService(repository).check_health()
    except Exception:
        healthy = False
    typer.echo(
        json.dumps(
            {
                "status": "ok" if healthy else "error",
                "database": "connected" if healthy else "unavailable",
            }
        )
    )
    if not healthy:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
