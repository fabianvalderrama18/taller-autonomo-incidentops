"""Aceptación de salud, selección de motor y topología reproducible."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from src.adapters.inbound.api.app import create_app
from src.adapters.inbound.cli import app as cli
from src.adapters.outbound.factory import create_repository
from src.adapters.outbound.postgres_repository import PostgresIncidentRepository
from src.adapters.outbound.sqlite_repository import SQLiteIncidentRepository
from src.application.ports import IncidentRepositoryPort


def test_bdd_salud_operativa(monkeypatch):
    """Given almacenamiento disponible / When salud web y CLI / Then conectividad disponible."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}
    result = CliRunner().invoke(cli, ["health"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == response.json()


def test_bdd_salud_no_disponible(monkeypatch):
    """Given almacenamiento caído / When salud / Then indisponibilidad sin credenciales."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(SQLiteIncidentRepository, "check_health", lambda self: False)
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unavailable"}
    result = CliRunner().invoke(cli, ["health"])
    assert result.exit_code == 1
    assert json.loads(result.stdout) == response.json()


def test_bdd_seleccion_de_motor(monkeypatch):
    """Given URL SQLite/PostgreSQL / When persistencia / Then contrato común."""
    for url, cls in [
        ("sqlite:///:memory:", SQLiteIncidentRepository),
        ("postgresql://user:password@localhost/db", PostgresIncidentRepository),
    ]:
        monkeypatch.setenv("DATABASE_URL", url)
        repo = create_repository()
        assert isinstance(repo, cls)
        assert isinstance(repo, IncidentRepositoryPort)
        if isinstance(repo, SQLiteIncidentRepository):
            repo.close()
    with pytest.raises(ValueError):
        create_repository("mysql://localhost/db")


def test_bdd_runtime_reproducible():
    """Given proyecto y Compose / When topología / Then salud y volumen persistente."""
    root = Path(__file__).resolve().parents[1]
    compose = (root / "docker-compose.yml").read_text()
    for expected in [
        "postgres:16-alpine",
        "service_healthy",
        "pg_isready",
        "/health",
        "incidentops-data:/var/lib/postgresql/data",
    ]:
        assert expected in compose
    dockerfile = (root / "Dockerfile").read_text()
    assert "python:3.12-slim" in dockerfile and "uv sync --frozen" in dockerfile
    assert ".venv" in (root / ".dockerignore").read_text()


def test_connection_failure_is_503(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", "sqlite:////nonexistent-parent-incidentops/test.db"
    )
    with TestClient(create_app()) as client:
        assert client.get("/health").status_code == 503
    assert CliRunner().invoke(cli, ["health"]).exit_code == 1


def test_postgres_failure_uses_real_driver(monkeypatch):
    # Puerto local cerrado: prueba el manejo del error de conexión real sin daemon.
    import socket

    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
        monkeypatch.setenv(
            "DATABASE_URL", f"postgresql://test:test@127.0.0.1:{port}/test"
        )
        with TestClient(create_app()) as client:
            response = client.get("/health")
        assert response.status_code == 503
        assert response.json() == {"status": "error", "database": "unavailable"}


def test_closed_sqlite_health():
    repo = create_repository("sqlite:///:memory:")
    repo.close()
    assert repo.check_health() is False
