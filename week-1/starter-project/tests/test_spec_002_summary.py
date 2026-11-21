"""Escenarios BDD y comprobaciones de adaptador de la spec H002."""

import json

import pytest
from typer.testing import CliRunner

from src.adapters.inbound.cli import app as cli_app
from src.application.ports import IncidentRepositoryPort
from src.domain.models import Incident

REFERENCE_TIME = "2026-11-05T09:00:00"
INCIDENT_IDS = ("INC-A", "INC-B", "INC-C", "INC-D")
DETAIL_KEYS = {
    "incident_id",
    "title",
    "component",
    "severity",
    "status",
    "elapsed_minutes",
    "requires_escalation",
}


def _snapshot(repository: IncidentRepositoryPort) -> list[tuple[str, Incident | None]]:
    return [(incident_id, repository.get_incident(incident_id)) for incident_id in INCIDENT_IDS]


# --- Escenarios BDD: mapeo 1:1 con spec.md ---


def test_bdd_resumen_global_excluyendo_resueltos(
    summary_client, summary_repository: IncidentRepositoryPort
) -> None:
    """Given tres incidentes activos y uno resuelto.

    When se consulta el resumen global en el instante de referencia acordado.
    Then el total es 3, los incumplimientos 2 y el detalle enumera solo los activos.
    """
    before = _snapshot(summary_repository)
    response = summary_client.get(
        "/api/v1/incidents/summary", params={"reference_time": REFERENCE_TIME}
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"total_active", "breached_count", "incidents"}
    assert body["total_active"] == 3
    assert body["breached_count"] == 2
    assert [item["incident_id"] for item in body["incidents"]] == ["INC-A", "INC-B", "INC-C"]
    assert all(set(item) == DETAIL_KEYS for item in body["incidents"])

    by_id = {item["incident_id"]: item for item in body["incidents"]}
    assert by_id["INC-A"]["title"] == "Caída de la pasarela de pagos"
    assert by_id["INC-A"]["component"] == "payments-gateway"
    assert by_id["INC-A"]["severity"] == "P0"
    assert by_id["INC-A"]["status"] == "OPEN"
    assert by_id["INC-A"]["elapsed_minutes"] == 90
    assert by_id["INC-A"]["requires_escalation"] is True
    assert by_id["INC-B"]["elapsed_minutes"] == 200
    assert by_id["INC-B"]["requires_escalation"] is True
    assert by_id["INC-C"]["elapsed_minutes"] == 300
    assert by_id["INC-C"]["requires_escalation"] is True
    assert "INC-D" not in by_id
    assert _snapshot(summary_repository) == before  # FR-011: solo lectura


def test_bdd_consulta_equivalente_por_cli(summary_client, summary_runner: CliRunner) -> None:
    """Given el mismo conjunto de incidentes y el mismo instante de referencia.

    When se consulta el resumen por HTTP y por la terminal.
    Then ambos canales muestran el mismo total, incumplimientos y detalle.
    """
    http_response = summary_client.get(
        "/api/v1/incidents/summary", params={"reference_time": REFERENCE_TIME}
    )
    result = summary_runner.invoke(cli_app, ["summary", "--reference-time", REFERENCE_TIME])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == http_response.json()


def test_bdd_resumen_filtrado_por_componente(summary_client) -> None:
    """Given activos en dos componentes distintos.

    When se filtra el resumen por el componente de pagos.
    Then solo se detallan sus dos incidentes y los totales se recalculan.
    """
    response = summary_client.get(
        "/api/v1/incidents/summary",
        params={"component": "payments-gateway", "reference_time": REFERENCE_TIME},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_active"] == 2
    assert body["breached_count"] == 1
    assert [item["incident_id"] for item in body["incidents"]] == ["INC-A", "INC-B"]

    spaces = summary_client.get(
        "/api/v1/incidents/summary",
        params={"component": "   ", "reference_time": REFERENCE_TIME},
    )
    assert spaces.status_code == 200
    assert spaces.json()["total_active"] == 3
    assert spaces.json()["breached_count"] == 2


def test_bdd_caso_vacio(summary_client, summary_runner: CliRunner) -> None:
    """Given que no hay coincidencias para el componente solicitado.

    When se consulta el resumen.
    Then la consulta tiene éxito, los totales son cero y el detalle está vacío.
    """
    expected = {"total_active": 0, "breached_count": 0, "incidents": []}
    params = {"component": "frontend-ui", "reference_time": REFERENCE_TIME}
    response = summary_client.get("/api/v1/incidents/summary", params=params)
    assert response.status_code == 200
    assert response.json() == expected

    result = summary_runner.invoke(
        cli_app,
        ["summary", "--component", "frontend-ui", "--reference-time", REFERENCE_TIME],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == expected


# --- Comprobaciones de adaptador y de persistencia (no BDD) ---


def test_repositorio_cumple_puerto(summary_repository: IncidentRepositoryPort) -> None:
    assert isinstance(summary_repository, IncidentRepositoryPort)


def test_check_health(summary_repository: IncidentRepositoryPort) -> None:
    assert summary_repository.check_health() is True


def test_operaciones_de_persistencia_preparacion_h003(
    summary_repository: IncidentRepositoryPort, canonical_incidents: list[Incident]
) -> None:
    assert summary_repository.get_incident("INC-A") == canonical_incidents[0]
    assert summary_repository.get_incident("NO-EXISTE") is None
    duplicates = summary_repository.find_open_duplicates("payments-gateway", "P0")
    assert [incident.incident_id for incident in duplicates] == ["INC-A"]


@pytest.mark.parametrize(
    "value",
    [
        "2026-11-05",
        "2026-11-05T09:00:00+00:00",
        "2026-11-05T09:00:00Z",
        "no-es-una-fecha",
    ],
)
def test_reference_time_invalida_se_rechaza_http(summary_client, value: str) -> None:
    response = summary_client.get(
        "/api/v1/incidents/summary", params={"reference_time": value}
    )
    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.parametrize(
    "value",
    [
        "2026-11-05",
        "2026-11-05T09:00:00+00:00",
    ],
)
def test_reference_time_invalida_se_rechaza_cli(summary_runner: CliRunner, value: str) -> None:
    result = summary_runner.invoke(cli_app, ["summary", "--reference-time", value])
    assert result.exit_code == 1
    assert "reference_time" in result.output + getattr(result, "stderr", "")


def test_reference_time_anterior_a_creacion_se_rechaza_http(summary_client) -> None:
    response = summary_client.get(
        "/api/v1/incidents/summary", params={"reference_time": "2026-11-05T03:00:00"}
    )
    assert response.status_code == 422
    assert "creación" in response.json()["detail"]


def test_reference_time_anterior_a_creacion_se_rechaza_cli(summary_runner: CliRunner) -> None:
    result = summary_runner.invoke(
        cli_app, ["summary", "--reference-time", "2026-11-05T03:00:00"]
    )
    assert result.exit_code == 1
