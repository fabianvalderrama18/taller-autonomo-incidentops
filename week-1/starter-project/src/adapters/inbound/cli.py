"""Adaptador CLI para el triaje y el resumen de incidentes."""

import json
from dataclasses import asdict
from typing import Annotated

import typer

from src.adapters.inbound.api.schemas import ActiveIncidentsSummaryResponse
from src.adapters.inbound.reference_time import parse_reference_time
from src.adapters.outbound.factory import create_incident_repository
from src.application.services import IncidentService, ValidationError

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
        service = IncidentService(create_incident_repository())
        result = service.get_active_incidents_summary(component, instant)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(ActiveIncidentsSummaryResponse.model_validate(result).model_dump_json())


if __name__ == "__main__":
    app()
