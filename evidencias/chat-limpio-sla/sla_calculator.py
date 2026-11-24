"""Calculador de SLA IncidentOps. Fechas naive en hora local única.

P0/P1: continuo. P2/P3: lunes-viernes [08:00, 18:00).
Sin festivos. Tiempo O(D), memoria O(1) para horario hábil.
"""
from datetime import datetime, time, timedelta
from typing import Dict

try:
    from .models import Incident, SLAEvaluation, SLARule, SeverityLevel
except ImportError:
    from models import Incident, SLAEvaluation, SLARule, SeverityLevel

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


def _demo() -> None:
    """Pruebas autocontenidas: una discrepancia provoca AssertionError."""
    def dt(day, hour, minute=0, second=0):
        return datetime(2026, 11, day, hour, minute, second)

    cases = [
        ('P2 viernes-lunes', 'P2', dt(6,17), dt(9,9), 120, False, False),
        ('P2 viernes fuera horario', 'P2', dt(6,18,30), dt(9,8,30), 30, False, False),
        ('P2 sabado-lunes', 'P2', dt(7,10), dt(9,8,30), 30, False, False),
        ('P3 fin semana', 'P3', dt(7,10), dt(8,17), 0, False, False),
        ('P3 jornada', 'P3', dt(9,8), dt(9,18), 600, False, False),
        ('P1 sabado', 'P1', dt(7,10), dt(7,13), 180, False, True),
        ('P2 umbral', 'P2', dt(9,8), dt(9,14), 360, False, True),
        ('P2 vencido', 'P2', dt(9,8), dt(9,16,1), 481, True, True),
        ('P0 limite', 'P0', dt(9,8), dt(9,9), 60, False, True),
        ('P0 limite +1s', 'P0', dt(9,8), dt(9,9,0,1), 60, True, True),
        ('P2 limite +1s', 'P2', dt(9,8), dt(9,16,0,1), 480, True, True),
        ('P0 antes umbral', 'P0', dt(9,8), dt(9,8,44,59), 44, False, False),
        ('P0 umbral exacto', 'P0', dt(9,8), dt(9,8,45), 45, False, True),
        ('P2 fuera jornada', 'P2', dt(9,18), dt(10,8), 0, False, False),
    ]
    for name, severity, start, end, minutes, breached, escalation in cases:
        incident = Incident(name, 'Prueba', 'IncidentOps', severity, 'OPEN', start)
        result = evaluate_sla_status(incident, end)
        allowed = SLA_POLICY_TABLE[severity].max_resolution_minutes
        assert (result.incident_id, result.severity, result.elapsed_minutes, result.allowed_minutes, result.remaining_minutes, result.is_breached, result.requires_escalation) == (name, severity, minutes, allowed, allowed-minutes, breached, escalation), (name, result)
        print(f'OK | {name} | {minutes} minutos')

    for name, status, resolved_at, minutes in [
        ('Cierre detiene reloj', 'OPEN', dt(9,10), 120),
        ('Resuelto sin escalamiento', 'RESOLVED', dt(9,11), 180),
    ]:
        incident = Incident(name, 'Prueba', 'IncidentOps', 'P1', status, dt(9,8), resolved_at)
        result = evaluate_sla_status(incident, dt(9,18))
        assert result.elapsed_minutes == minutes and not result.requires_escalation, (name, result)
        print(f'OK | {name} | {minutes} minutos')

    from datetime import timezone
    base = Incident('INVALID', 'Prueba', 'IncidentOps', 'P2', 'OPEN', dt(9,10))
    invalid = [
        ('Intervalo invertido', base, dt(9,9)),
        ('Referencia aware', base, dt(9,11).replace(tzinfo=timezone.utc)),
        ('Creacion aware', Incident('AWARE', 'Prueba', 'IncidentOps', 'P2', 'OPEN', dt(9,8).replace(tzinfo=timezone.utc)), dt(9,10)),
        ('Cierre aware', Incident('CLOSE', 'Prueba', 'IncidentOps', 'P2', 'OPEN', dt(9,8), dt(9,9).replace(tzinfo=timezone.utc)), dt(9,10)),
    ]
    for name, incident, reference in invalid:
        try:
            evaluate_sla_status(incident, reference)
        except ValueError:
            print(f'OK | {name} | ValueError')
        else:
            raise AssertionError(f'{name}: se esperaba ValueError')
    try:
        get_sla_rule_for_severity('P9')
    except ValueError:
        print('OK | Severidad invalida | ValueError')
    else:
        raise AssertionError('Se esperaba ValueError para P9')
    print('Todas las comprobaciones finalizaron correctamente.')


if __name__ == '__main__':
    _demo()
