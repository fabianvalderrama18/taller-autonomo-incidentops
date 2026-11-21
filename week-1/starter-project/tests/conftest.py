"""Fixtures compartidas para las pruebas de aceptación."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from src.adapters.inbound.api.app import create_app
from src.adapters.inbound.cli import app as cli_app
from src.adapters.outbound.factory import create_incident_repository
from src.application.ports import IncidentRepositoryPort
from src.domain.models import Incident


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def canonical_incidents() -> list[Incident]:
    """Dataset canónico de `data-model.md > Dataset canónico de aceptación`."""
    return [
        Incident(
            "INC-A",
            "Caída de la pasarela de pagos",
            "payments-gateway",
            "P0",
            "OPEN",
            datetime(2026, 11, 5, 7, 30, 0),
        ),
        Incident(
            "INC-B",
            "Timeouts intermitentes en pagos",
            "payments-gateway",
            "P1",
            "IN_PROGRESS",
            datetime(2026, 11, 5, 5, 40, 0),
        ),
        Incident(
            "INC-C",
            "Error de autenticación corporativa",
            "auth-identity",
            "P1",
            "OPEN",
            datetime(2026, 11, 5, 4, 0, 0),
        ),
        Incident(
            "INC-D",
            "Informe histórico lento",
            "reporting-api",
            "P3",
            "RESOLVED",
            datetime(2026, 11, 5, 8, 30, 0),
            datetime(2026, 11, 5, 9, 0, 0),
        ),
    ]


@pytest.fixture
def summary_database_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, canonical_incidents: list[Incident]
) -> str:
    """Base aislada por prueba; HTTP y CLI la comparten vía `DATABASE_URL`."""
    url = f"sqlite:///{tmp_path / 'incidents.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    repository = create_incident_repository(url)
    for incident in canonical_incidents:
        repository.save_incident(incident)
    return url


@pytest.fixture
def summary_repository(summary_database_url: str) -> IncidentRepositoryPort:
    return create_incident_repository(summary_database_url)


@pytest.fixture
def summary_client(summary_database_url: str) -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def summary_runner(summary_database_url: str) -> CliRunner:
    return CliRunner()


@pytest.fixture
def canonical_reports() -> dict[str, dict[str, Any]]:
    path = Path(__file__).resolve().parents[1] / "data" / "sample_incidents.json"
    reports: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    return {report["id"]: report for report in reports}
