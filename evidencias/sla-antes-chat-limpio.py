"""Cálculo determinista de SLA: tiempo continuo o jornada local sin zona."""
from datetime import datetime, time, timedelta
from typing import Dict

from src.models import Incident, SLAEvaluation, SLARule, SeverityLevel

SLA_POLICY_TABLE: Dict[SeverityLevel, SLARule] = {
    "P0": SLARule(severity="P0", max_resolution_minutes=60, operates_24x7=True),
    "P1": SLARule(severity="P1", max_resolution_minutes=240, operates_24x7=True),
    "P2": SLARule(severity="P2", max_resolution_minutes=480, operates_24x7=False),
    "P3": SLARule(severity="P3", max_resolution_minutes=1440, operates_24x7=False),
}


def get_sla_rule_for_severity(severity: SeverityLevel) -> SLARule:
    if severity not in SLA_POLICY_TABLE:
        raise ValueError(f"Severidad no válida: {severity}")
    return SLA_POLICY_TABLE[severity]


def _business_seconds(start: datetime, end: datetime) -> float:
    """Intersección con [08:00,18:00), lunes a viernes; O(días), O(1) memoria."""
    day = start.date()
    last_day = end.date()
    total = 0.0
    while day <= last_day:
        if day.weekday() < 5:
            opening = datetime.combine(day, time(8))
            closing = datetime.combine(day, time(18))
            left, right = max(start, opening), min(end, closing)
            if right > left:
                total += (right - left).total_seconds()
        if day == last_day:
            break  # Evita desbordar date.max después de procesar el último día.
        day += timedelta(days=1)
    return total


def evaluate_sla_status(incident: Incident, reference_time: datetime) -> SLAEvaluation:
    """Evalúa en una única hora local de negocio, con datetime sin zona.

    resolved_at detiene el reloj. Los umbrales usan segundos exactos; los
    campos públicos conservan minutos enteros. No modifica el incidente.
    """
    rule = get_sla_rule_for_severity(incident.severity)
    end_time = incident.resolved_at or reference_time
    for stamp in (incident.created_at, reference_time, end_time):
        if stamp.tzinfo is not None:
            raise ValueError("Use fechas sin zona en una misma hora local de negocio.")
    if end_time < incident.created_at:
        raise ValueError("El tiempo de referencia o cierre no puede ser anterior a la creación.")

    seconds = ((end_time - incident.created_at).total_seconds()
               if rule.operates_24x7
               else _business_seconds(incident.created_at, end_time))
    elapsed_minutes = int(seconds // 60)
    allowed_seconds = rule.max_resolution_minutes * 60
    is_breached = seconds > allowed_seconds
    is_resolved = incident.status == "RESOLVED" or incident.resolved_at is not None
    requires_escalation = (
        not is_resolved
        and (is_breached or seconds >= allowed_seconds * rule.escalation_threshold_ratio)
    )
    return SLAEvaluation(
        incident_id=incident.incident_id,
        severity=incident.severity,
        elapsed_minutes=elapsed_minutes,
        allowed_minutes=rule.max_resolution_minutes,
        remaining_minutes=rule.max_resolution_minutes - elapsed_minutes,
        is_breached=is_breached,
        requires_escalation=requires_escalation,
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
