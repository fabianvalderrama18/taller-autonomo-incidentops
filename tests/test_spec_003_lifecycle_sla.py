"""Aceptación de ciclo de vida (spec 003)."""

import json
import re
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from src.adapters.inbound.api.app import create_app
from src.adapters.inbound.cli import app as cli
from src.adapters.outbound.factory import create_repository

REPORT = "Mi cuenta individual está bloqueada hoy y no puedo acceder"
BODY = dict(title="Cuenta bloqueada", raw_text=REPORT, created_at="2026-11-06T17:00:00")


@pytest.fixture
def lifecycle(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'lifecycle.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    with TestClient(create_app()) as client:
        yield client, CliRunner(), url


def test_bdd_registro_inicial(lifecycle):
    """Given sin equivalentes / When registro válido / Then clasificación sin duplicados."""
    client, _, url = lifecycle
    response = client.post("/api/v1/incidents", json=BODY)
    assert response.status_code == 201
    body = response.json()
    assert re.fullmatch(r"INC-[A-F0-9]{8}", body["incident_id"])
    assert body["severity"] == "P2"
    assert body["recommended_team"] == "Security-IAM"
    assert body["is_duplicate"] is False and body["duplicate_of"] == []
    repo = create_repository(url)
    assert (
        repo.get_incident(body["incident_id"]).duplicate_group_key
        == body["duplicate_group_key"]
    )
    repo.close()


def test_bdd_duplicado_abierto(lifecycle):
    """Given equivalentes abiertos y resueltos / When registro / Then solo abiertos sin propio ID."""
    client, _, url = lifecycle
    for identifier, status in [
        ("A", "OPEN"),
        ("B", "IN_PROGRESS"),
        ("C", "ESCALATION_REQUIRED"),
        ("D", "RESOLVED"),
    ]:
        assert (
            client.post(
                "/api/v1/incidents",
                json={**BODY, "incident_id": identifier, "status": status},
            ).status_code
            == 201
        )
    response = client.post("/api/v1/incidents", json={**BODY, "incident_id": "E"})
    assert response.json()["duplicate_of"] == ["A", "B", "C"]
    assert response.json()["is_duplicate"] is True
    repo = create_repository(url)
    item = repo.get_incident("A")
    item.severity = "P1"  # La clave, no la severidad, define equivalencia.
    repo.save_incident(item)
    assert [
        i.incident_id for i in repo.find_open_duplicates(item.duplicate_group_key, "E")
    ] == ["A", "B", "C"]
    item.duplicate_group_key = "otro-sintoma"
    repo.save_incident(item)
    assert [i.incident_id for i in repo.find_open_duplicates("otro-sintoma")] == ["A"]
    repo.close()


def test_bdd_sla_habil(lifecycle):
    """Given P2 viernes 17 / When lunes 09 / Then 120 usados, 480 permitidos y 360 restantes."""
    client, _, _ = lifecycle
    client.post("/api/v1/incidents", json={**BODY, "incident_id": "A"})
    response = client.get(
        "/api/v1/incidents/A/sla", params={"reference_time": "2026-11-09T09:00:00"}
    )
    assert response.status_code == 200
    assert response.json() == dict(
        incident_id="A",
        severity="P2",
        elapsed_minutes=120,
        allowed_minutes=480,
        remaining_minutes=360,
        is_breached=False,
        requires_escalation=False,
    )


def test_bdd_errores_de_auditoria(lifecycle):
    """Given ID ausente o tiempo anterior / When auditoría / Then ausencia o entrada inválida."""
    client, runner, _ = lifecycle
    assert client.get("/api/v1/incidents/missing/sla").status_code == 404
    client.post("/api/v1/incidents", json={**BODY, "incident_id": "A"})
    assert (
        client.get(
            "/api/v1/incidents/A/sla", params={"reference_time": "2026-11-05T17:00:00"}
        ).status_code
        == 422
    )
    assert runner.invoke(cli, ["sla", "--incident-id", "missing"]).exit_code == 1
    assert (
        runner.invoke(
            cli,
            ["sla", "--incident-id", "A", "--reference-time", "2026-11-05T17:00:00"],
        ).exit_code
        == 1
    )


def test_bdd_paridad_cli(lifecycle, monkeypatch, tmp_path):
    """Given mismo reporte/referencia / When web y terminal / Then resultados equivalentes."""
    client, runner, _ = lifecycle
    response = client.post("/api/v1/incidents", json={**BODY, "incident_id": "A"})
    expected = client.get(
        "/api/v1/incidents/A/sla", params={"reference_time": "2026-11-09T09:00:00"}
    ).json()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cli.db'}")
    result = runner.invoke(
        cli,
        [
            "create",
            "--title",
            BODY["title"],
            "--raw-text",
            REPORT,
            "--incident-id",
            "A",
            "--created-at",
            BODY["created_at"],
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == response.json()
    result = runner.invoke(
        cli, ["sla", "--incident-id", "A", "--reference-time", "2026-11-09T09:00:00"]
    )
    assert result.exit_code == 0
    assert json.loads(result.stdout) == expected


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", ""),
        ("title", "  "),
        ("raw_text", " "),
        ("incident_id", ""),
        ("status", "INVALID"),
        ("created_at", "2026-11-06"),
    ],
)
def test_invalid_create(lifecycle, field, value):
    client, _, _ = lifecycle
    assert (
        client.post("/api/v1/incidents", json={**BODY, field: value}).status_code == 422
    )


def test_collision_and_timezone(lifecycle):
    client, runner, _ = lifecycle
    body = {**BODY, "incident_id": "A", "created_at": "2026-11-06T22:00:00Z"}
    assert (
        client.post("/api/v1/incidents", json=body).json()["created_at"]
        == BODY["created_at"]
    )
    assert client.post("/api/v1/incidents", json=body).status_code == 409
    response = client.get(
        "/api/v1/incidents/A/sla",
        params={"reference_time": "2026-11-09T14:00:00+00:00"},
    )
    assert response.json()["elapsed_minutes"] == 120
    assert (
        runner.invoke(cli, ["create", "--title", " ", "--raw-text", REPORT]).exit_code
        == 1
    )


def test_memory_lifetime(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(create_app()) as client:
        assert (
            client.post(
                "/api/v1/incidents", json={**BODY, "incident_id": "A"}
            ).status_code
            == 201
        )
        assert (
            client.get(
                "/api/v1/incidents/A/sla",
                params={"reference_time": "2026-11-09T09:00:00"},
            ).status_code
            == 200
        )


def test_sqlite_migrates_existing_schema(tmp_path):
    import sqlite3

    path = tmp_path / "old.db"
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE incidents (incident_id TEXT PRIMARY KEY, title TEXT, component TEXT, severity TEXT, status TEXT, created_at TEXT, resolved_at TEXT)"
        )
        conn.execute(
            "INSERT INTO incidents VALUES ('old','old','auth','P2','OPEN','2026-11-06T17:00:00',NULL)"
        )
    repo = create_repository(f"sqlite:///{path}")
    assert repo.get_incident("old").created_at == datetime(2026, 11, 6, 17)
    assert repo.get_incident("old").duplicate_group_key is None
    repo.close()
