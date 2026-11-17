"""Calculador de SLA IncidentOps. Fechas naive en hora local única.

P0/P1: continuo. P2/P3: lunes-viernes [08:00, 18:00).
Sin festivos. Tiempo O(D), memoria O(1) para horario hábil.
"""
from datetime import datetime, time, timedelta
from typing import Dict

from src.models import Incident, SLAEvaluation, SLARule, SeverityLevel

BUSINESS_START = time(8)
BUSINESS_END = time(18)
SLA_POLICY_TABLE: Dict[SeverityLevel, SLARule] = {
    'P0': SLARule('P0', 60, True),
    'P1': SLARule('P1', 240, True),
    'P2': SLARule('P2', 480, False),
    'P3': SLARule('P3', 1440, False),
}


def get_sla_rule_for_severity(severity: SeverityLevel) -> SLARule:
    """Obtiene la regla SLA o rechaza severidades desconocidas."""
    if severity not in SLA_POLICY_TABLE:
        raise ValueError(f'Severidad no válida: {severity}')
    return SLA_POLICY_TABLE[severity]


def _validate_interval(start: datetime, end: datetime) -> None:
    if start.tzinfo is not None or end.tzinfo is not None:
        raise ValueError('Las fechas deben ser naive, sin zona horaria.')
    if end < start:
        raise ValueError('El tiempo final no puede ser anterior a la creación.')


def _business_elapsed(start: datetime, end: datetime) -> timedelta:
    """Suma intersecciones diarias exactas, sin listas ni minutos iterados."""
    total = timedelta(0)
    day = start.date()
    last = end.date()
    while day <= last:
        if day.weekday() < 5:
            opening = datetime.combine(day, BUSINESS_START)
            closing = datetime.combine(day, BUSINESS_END)
            overlap_start = max(start, opening)
            overlap_end = min(end, closing)
            if overlap_end > overlap_start:
                total += overlap_end - overlap_start
        if day == last:
            break
        day += timedelta(days=1)
    return total


def evaluate_sla_status(incident: Incident, reference_time: datetime) -> SLAEvaluation:
    """Evalúa SLA con segundos exactos y minutos públicos truncados."""
    rule = get_sla_rule_for_severity(incident.severity)
    end = incident.resolved_at if incident.resolved_at is not None else reference_time
    _validate_interval(incident.created_at, end)
    elapsed = (end - incident.created_at) if rule.operates_24x7 else _business_elapsed(incident.created_at, end)
    allowed = timedelta(minutes=rule.max_resolution_minutes)
    elapsed_minutes = elapsed // timedelta(minutes=1)
    resolved = incident.status == 'RESOLVED' or incident.resolved_at is not None
    return SLAEvaluation(
        incident_id=incident.incident_id,
        severity=incident.severity,
        elapsed_minutes=elapsed_minutes,
        allowed_minutes=rule.max_resolution_minutes,
        remaining_minutes=rule.max_resolution_minutes - elapsed_minutes,
        is_breached=elapsed > allowed,
        requires_escalation=not resolved and elapsed >= allowed * rule.escalation_threshold_ratio,
    )


def _run_demo() -> None:
    # Nombre, severidad, inicio, fin, minutos, vencido, escalamiento.
    cases = [
        ("Viernes a lunes", "P2", "2026-11-06T17:00", "2026-11-09T09:00", 120, False, False),
        ("Creación fuera de jornada", "P2", "2026-11-06T18:30", "2026-11-09T08:30", 30, False, False),
        ("Creación en sábado", "P2", "2026-11-07T10:00", "2026-11-09T08:30", 30, False, False),
        ("Solo fin de semana", "P3", "2026-11-07T08:00", "2026-11-08T18:00", 0, False, False),
        ("Jornada completa", "P3", "2026-11-09T08:00", "2026-11-09T18:00", 600, False, False),
        ("P1 continuo en fin de semana", "P1", "2026-11-07T10:00", "2026-11-07T13:00", 180, False, True),
        ("Umbral P2 al 75%", "P2", "2026-11-09T08:00", "2026-11-09T14:00", 360, False, True),
        ("P2 vencido mantiene escalamiento", "P2", "2026-11-09T08:00", "2026-11-09T16:01", 481, True, True),
        ("P0 exactamente al plazo", "P0", "2026-11-08T08:00", "2026-11-08T09:00", 60, False, True),
        ("P0 supera el plazo un segundo", "P0", "2026-11-08T08:00", "2026-11-08T09:00:01", 60, True, True),
        ("Varios fines de semana", "P3", "2026-11-06T17:00", "2026-11-16T09:00", 3120, True, True),
    ]
    for idx, (name, severity, start, end, minutes, breached, escalation) in enumerate(cases):
        incident = Incident(str(idx), name, "reporting-api", severity, "OPEN", datetime.fromisoformat(start))
        result = evaluate_sla_status(incident, datetime.fromisoformat(end))
        actual = (result.elapsed_minutes, result.is_breached, result.requires_escalation)
        expected = (minutes, breached, escalation)
        if actual != expected:
            raise AssertionError(f"{name}: esperado {expected}, obtenido {actual}")
        print(f"OK | {name} | {result.elapsed_minutes} min | vencido={result.is_breached} | escalar={result.requires_escalation}")
    print(f"VERIFICACION OK: {len(cases)} casos de SLA.")


if __name__ == "__main__":
    _run_demo()
