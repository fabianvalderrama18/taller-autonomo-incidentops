"""Escenarios BDD de la spec H001 (HTTP y CLI)."""

import json

import pytest

from src.adapters.inbound.cli import app as cli_app


def test_bdd_caida_critica_http_502_en_pasarela_de_pagos(client, canonical_reports):
    """Given un reporte de indisponibilidad generalizada de pagos con HTTP 502.

    When se envía mediante POST /api/v1/incidents/triage.
    Then la respuesta es 200 con P0, payments-gateway, Backend-Core y la clave canónica.
    """
    report = canonical_reports["INC-1001"]
    response = client.post(
        "/api/v1/incidents/triage",
        json={"incident_id": report["id"], "raw_text": report["raw_text"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["severity"] == "P0"
    assert body["component"] == "payments-gateway"
    assert body["recommended_team"] == "Backend-Core"
    assert body["duplicate_group_key"] == "payments-gateway:payment_http_502"
    assert set(body) == {
        "incident_id",
        "severity",
        "component",
        "rationale",
        "recommended_team",
        "duplicate_group_key",
        "consistency_ratio",
    }


def test_bdd_cuenta_individual_bloqueada_mencionando_hoy(client, canonical_reports):
    """Given un reporte de bloqueo de cuenta individual que incluye la palabra "hoy".

    When se clasifica mediante el endpoint HTTP.
    Then la respuesta es 200 con P2 y Security-IAM, sin falso positivo P0.
    """
    report = canonical_reports["INC-1002"]
    response = client.post(
        "/api/v1/incidents/triage",
        json={"incident_id": report["id"], "raw_text": report["raw_text"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["severity"] == "P2"
    assert body["recommended_team"] == "Security-IAM"


@pytest.mark.parametrize(
    "payload",
    [
        {"incident_id": "INC-1001", "raw_text": " "},
        {"incident_id": "", "raw_text": "Reporte de prueba"},
    ],
)
def test_bdd_entradas_vacias_o_con_solo_espacios(client, payload):
    """Given raw_text=" " o incident_id="".

    When se envía la petición al endpoint HTTP.
    Then se devuelve 422 Unprocessable Entity y no se clasifica el reporte.
    """
    response = client.post("/api/v1/incidents/triage", json=payload)
    assert response.status_code == 422


def test_bdd_paridad_en_cli(runner, canonical_reports):
    """Given el reporte canónico INC-1001.

    When se ejecuta el subcomando triage en la CLI.
    Then imprime JSON válido en stdout con P0 y Backend-Core, y termina con código 0.
    """
    report = canonical_reports["INC-1001"]
    result = runner.invoke(
        cli_app,
        ["triage", "--incident-id", report["id"], "--raw-text", report["raw_text"]],
    )
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["severity"] == "P0"
    assert body["recommended_team"] == "Backend-Core"


def test_bdd_entradas_vacias_en_la_cli(runner):
    """Given raw_text="   " o incident_id="".

    When se ejecuta el subcomando triage en la CLI.
    Then la CLI termina con error y código de salida 1.
    """
    result = runner.invoke(
        cli_app,
        ["triage", "--incident-id", "INC-1001", "--raw-text", "   "],
    )
    assert result.exit_code == 1
