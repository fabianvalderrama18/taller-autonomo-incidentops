"""Reglas deterministas de triaje para IncidentOps."""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, Tuple

from src.domain.models import SeverityLevel, TriageResult


def _normalize(text: str) -> str:
    """Normaliza acentos, mayúsculas y espacios sin alterar la semántica."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return " ".join(without_accents.lower().split())


def _has_any(text: str, terms: Iterable[str]) -> bool:
    return any(term in text for term in terms)


def _result(
    incident_id: str,
    severity: SeverityLevel,
    component: str,
    recommended_team: str,
    duplicate_group_key: str,
    rationale: str,
) -> TriageResult:
    return TriageResult(
        incident_id=incident_id,
        severity=severity,
        component=component,
        rationale=rationale,
        recommended_team=recommended_team,
        duplicate_group_key=duplicate_group_key,
    )


def classify_incident_report(
    incident_id: str,
    raw_text: str,
) -> TriageResult:
    """Clasifica un reporte mediante reglas deterministas con precedencia explícita.

    Precedencia:
    1. Exposición de datos entre organizaciones.
    2. Indisponibilidad generalizada de pagos.
    3. Interrupción de pagos de alcance limitado.
    4. Saturación de base de datos con timeouts.
    5. Bloqueo de cuenta individual.
    6. Latencia asociada a conjuntos de datos grandes.
    7. Exportación lenta que termina correctamente.
    8. Solicitud cosmética.
    9. Mantenimiento preventivo de certificados de staging.
    10. Respaldo conservador para casos no reconocidos.

    "hoy", "urgente" y un HTTP 502 aislado no determinan severidad
    ni componente.
    """
    text = _normalize(raw_text)

    cross_tenant_exposure = (
        "otra organizacion" in text
        and _has_any(
            text,
            (
                "company_id",
                "factura",
                "facturas",
                "reporte",
                "pdf",
            ),
        )
        and _has_any(
            text,
            (
                "visualizar",
                "ver ",
                "acceso",
                "acceder",
                "pertenecientes",
            ),
        )
    )

    if cross_tenant_exposure:
        return _result(
            incident_id,
            "P0",
            "reporting-api",
            "Security-IAM",
            "reporting-api:cross_tenant_data_exposure",
            (
                "Exposición de facturas entre organizaciones "
                "por fallo de autorización."
            ),
        )

    payment_context = _has_any(
        text,
        (
            "pago",
            "pagos",
            "cobro",
            "cobros",
            "tarjeta",
            "carrito",
            "pasarela",
            "gateway de pagos",
        ),
    )

    payment_failure = _has_any(
        text,
        (
            "502",
            "bad gateway",
            "error",
            "cayo",
            "caida",
            "no puede cobrar",
            "no pueden cobrar",
        ),
    )

    global_payment_scope = _has_any(
        text,
        (
            "todas las transacciones",
            "ningun comercio",
            "todos los comercios",
            "nadie puede cobrar",
        ),
    )

    payment_group = (
        "payments-gateway:payment_http_502"
        if re.search(r"\b502\b", text)
        else "payments-gateway:payment_unavailable"
    )

    if payment_context and payment_failure and global_payment_scope:
        return _result(
            incident_id,
            "P0",
            "payments-gateway",
            "Backend-Core",
            payment_group,
            "Indisponibilidad generalizada de pagos que impide cobrar.",
        )

    if payment_context and payment_failure:
        return _result(
            incident_id,
            "P1",
            "payments-gateway",
            "Backend-Core",
            payment_group,
            (
                "Interrupción de pagos con alcance limitado "
                "al comercio reportante."
            ),
        )

    database_context = _has_any(
        text,
        (
            "postgresql",
            "base de datos",
            "pool de conexiones",
            "conexiones",
        ),
    )

    connection_pressure = (
        bool(re.search(r"\b9[0-9]\s*%", text))
        or _has_any(
            text,
            (
                "saturacion",
                "uso de conexiones",
            ),
        )
    )

    timeout_signal = _has_any(
        text,
        (
            "timeout",
            "timeouts",
            "tiempo de espera",
        ),
    )

    if database_context and connection_pressure and timeout_signal:
        return _result(
            incident_id,
            "P1",
            "database-cluster",
            "Data-DBA",
            "database-cluster:connection_saturation",
            (
                "Saturación de conexiones de base de datos "
                "acompañada de timeouts."
            ),
        )

    account_lockout = (
        _has_any(
            text,
            (
                "cuenta",
                "ingresar",
                "login",
                "autentic",
            ),
        )
        and _has_any(
            text,
            (
                "bloqueada",
                "bloqueado",
                "bloqueo",
            ),
        )
    )

    if account_lockout:
        return _result(
            incident_id,
            "P2",
            "auth-identity",
            "Security-IAM",
            "auth-identity:account_lockout",
            (
                "Bloqueo de una cuenta individual; requiere atención "
                "de identidad sin impacto generalizado."
            ),
        )

    latency_signal = _has_any(
        text,
        (
            "tarda",
            "lenta",
            "lento",
            "segundos",
            "latencia",
            "demora",
        ),
    )

    large_dataset_signal = (
        bool(re.search(r"\b10[.,]?000\b", text))
        or _has_any(
            text,
            (
                "mas de 10000",
                "gran volumen",
            ),
        )
    )

    reporting_context = _has_any(
        text,
        (
            "dashboard",
            "reportes",
            "historial",
            "registros",
            "ordenes",
            "planes",
            "listado",
        ),
    )

    if (
        latency_signal
        and large_dataset_signal
        and reporting_context
    ):
        return _result(
            incident_id,
            "P2",
            "reporting-api",
            "Backend-Core",
            "reporting-api:large_dataset_latency",
            (
                "Degradación de rendimiento al consultar "
                "conjuntos de datos grandes."
            ),
        )

    export_context = _has_any(
        text,
        (
            "exportacion",
            "exportar",
            "excel",
            "csv",
        ),
    )

    successful_download = _has_any(
        text,
        (
            "al final si descarga",
            "descarga el archivo completo",
            "archivo completo",
            "termina correctamente",
            "se descarga",
        ),
    )

    if (
        export_context
        and latency_signal
        and successful_download
    ):
        return _result(
            incident_id,
            "P2",
            "reporting-api",
            "Backend-Core",
            "reporting-api:export_latency",
            (
                "Exportación lenta que finaliza con "
                "la descarga completa del archivo."
            ),
        )

    cosmetic_request = (
        _has_any(
            text,
            (
                "color",
                "cosmetic",
                "visual",
            ),
        )
        and _has_any(
            text,
            (
                "boton",
                "interfaz",
                "ui",
                "resalta",
            ),
        )
    )

    if cosmetic_request:
        return _result(
            incident_id,
            "P3",
            "frontend-ui",
            "Backend-Core",
            "frontend-ui:cosmetic_request",
            "Solicitud cosmética de interfaz sin afectación operativa.",
        )

    certificate_context = _has_any(
        text,
        (
            "certificado",
            "tls",
            "ssl",
        ),
    )

    staging_context = _has_any(
        text,
        (
            "staging",
            "preproduccion",
            "pre-produccion",
        ),
    )

    preventive_context = _has_any(
        text,
        (
            "vencera",
            "vence en",
            "rotacion programada",
            "antes del proximo sprint",
        ),
    )

    if (
        certificate_context
        and staging_context
        and preventive_context
    ):
        return _result(
            incident_id,
            "P3",
            "infra-certificates",
            "Platform-SRE",
            "infra-certificates:staging_certificate_maintenance",
            (
                "Mantenimiento preventivo de certificado de staging "
                "sin afectación actual."
            ),
        )

    return _result(
        incident_id,
        "P3",
        "unknown-component",
        "Backend-Core",
        "unknown-component:unclassified_report",
        (
            "Reporte no reconocido por las reglas actuales; "
            "P3 provisional que requiere revisión manual; "
            "no acredita un impacto bajo."
        ),
    )


ExpectedClassification = Tuple[str, str, str, str]


EXPECTED: Dict[str, ExpectedClassification] = {
    "INC-1001": (
        "P0",
        "payments-gateway",
        "Backend-Core",
        "payments-gateway:payment_http_502",
    ),
    "INC-1002": (
        "P2",
        "auth-identity",
        "Security-IAM",
        "auth-identity:account_lockout",
    ),
    "INC-1003": (
        "P2",
        "reporting-api",
        "Backend-Core",
        "reporting-api:large_dataset_latency",
    ),
    "INC-1004": (
        "P3",
        "frontend-ui",
        "Backend-Core",
        "frontend-ui:cosmetic_request",
    ),
    "INC-1005": (
        "P1",
        "database-cluster",
        "Data-DBA",
        "database-cluster:connection_saturation",
    ),
    "INC-1006": (
        "P1",
        "payments-gateway",
        "Backend-Core",
        "payments-gateway:payment_http_502",
    ),
    "INC-1007": (
        "P0",
        "reporting-api",
        "Security-IAM",
        "reporting-api:cross_tenant_data_exposure",
    ),
    "INC-1008": (
        "P2",
        "reporting-api",
        "Backend-Core",
        "reporting-api:large_dataset_latency",
    ),
    "INC-1009": (
        "P2",
        "reporting-api",
        "Backend-Core",
        "reporting-api:export_latency",
    ),
    "INC-1010": (
        "P3",
        "infra-certificates",
        "Platform-SRE",
        "infra-certificates:staging_certificate_maintenance",
    ),
}


def _load_reports() -> list[dict[str, str]]:
    project_dir = Path(__file__).resolve().parents[2]
    data_path = project_dir / "data" / "sample_incidents.json"

    with data_path.open("r", encoding="utf-8") as handle:
        reports = json.load(handle)

    if not isinstance(reports, list):
        raise ValueError(
            "sample_incidents.json debe contener una lista de reportes."
        )

    return reports


def _classification_tuple(
    result: TriageResult,
) -> ExpectedClassification:
    return (
        result.severity,
        result.component,
        result.recommended_team,
        result.duplicate_group_key,
    )


def _verify_regressions(
    reports_by_id: Dict[str, dict[str, str]],
) -> list[str]:
    failures: list[str] = []

    individual_text = reports_by_id["INC-1002"]["raw_text"]

    baseline = classify_incident_report(
        "REG-BASE",
        individual_text,
    )

    noisy = classify_incident_report(
        "REG-NOISY",
        f"URGENTE: {individual_text} hoy",
    )

    if _classification_tuple(noisy) != _classification_tuple(baseline):
        failures.append(
            "'hoy'/'urgente' alteraron la clasificación "
            "de un caso individual."
        )

    unrelated_502 = classify_incident_report(
        "REG-502",
        (
            "El servicio de notificaciones devuelve "
            "HTTP 502 al publicar mensajes."
        ),
    )

    if unrelated_502.component == "payments-gateway":
        failures.append(
            "Un HTTP 502 ajeno a pagos fue clasificado "
            "como payments-gateway."
        )

    original_text = reports_by_id["INC-1006"]["raw_text"]

    original = classify_incident_report(
        "INC-1006",
        original_text,
    )

    changed_id = classify_incident_report(
        "INC-9999",
        original_text,
    )

    if _classification_tuple(original) != _classification_tuple(changed_id):
        failures.append(
            "Cambiar el incident_id alteró la clasificación."
        )

    export_result = classify_incident_report(
        "REG-EXPORT",
        reports_by_id["INC-1009"]["raw_text"],
    )

    rationale = _normalize(export_result.rationale)

    if (
        export_result.severity != "P2"
        or export_result.component != "reporting-api"
        or "descarga completa" not in rationale
        or "fallida" in rationale
        or "fallo de exportacion" in rationale
    ):
        failures.append(
            "La exportación lenta y exitosa no quedó "
            "descrita correctamente."
        )

    return failures


def main() -> int:
    reports = _load_reports()

    reports_by_id = {
        item["id"]: item
        for item in reports
    }

    failures: list[str] = []

    if len(reports) != 10:
        failures.append(
            f"Se esperaban 10 reportes y se cargaron {len(reports)}."
        )

    print("Resultados de triaje:")

    for item in reports:
        result = classify_incident_report(
            item["id"],
            item["raw_text"],
        )

        print(
            f"{result.incident_id} | "
            f"{result.severity} | "
            f"{result.component} | "
            f"{result.recommended_team} | "
            f"{result.duplicate_group_key} | "
            f"{result.rationale}"
        )

        expected = EXPECTED.get(item["id"])

        if expected is None:
            failures.append(
                f"No hay expectativa definida para {item['id']}."
            )
        elif _classification_tuple(result) != expected:
            failures.append(
                f"{item['id']}: "
                f"esperado={expected}, "
                f"obtenido={_classification_tuple(result)}"
            )

    if set(reports_by_id) != set(EXPECTED):
        failures.append(
            "Los IDs del JSON no coinciden exactamente "
            "con los 10 casos esperados."
        )

    first_payment = classify_incident_report(
        "PAIR-A",
        reports_by_id["INC-1001"]["raw_text"],
    )

    second_payment = classify_incident_report(
        "PAIR-B",
        reports_by_id["INC-1006"]["raw_text"],
    )

    if (
        first_payment.duplicate_group_key
        != second_payment.duplicate_group_key
    ):
        failures.append(
            "INC-1001 e INC-1006 no comparten clave de duplicados."
        )

    first_latency = classify_incident_report(
        "PAIR-C",
        reports_by_id["INC-1003"]["raw_text"],
    )

    second_latency = classify_incident_report(
        "PAIR-D",
        reports_by_id["INC-1008"]["raw_text"],
    )

    if (
        first_latency.duplicate_group_key
        != second_latency.duplicate_group_key
    ):
        failures.append(
            "INC-1003 e INC-1008 no comparten clave de duplicados."
        )

    failures.extend(
        _verify_regressions(reports_by_id)
    )

    if failures:
        print(
            "\nVERIFICACION FALLIDA:",
            file=sys.stderr,
        )

        for failure in failures:
            print(
                f"- {failure}",
                file=sys.stderr,
            )

        return 1

    print(
        "\nVERIFICACION OK: "
        "10 casos esperados y regresiones superadas."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
