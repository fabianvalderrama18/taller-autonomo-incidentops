# Contrato HTTP — Resumen de incidentes activos

**Endpoint**: `GET /api/v1/incidents/summary`
**Adaptador**: `src/adapters/inbound/api/app.py`
**Caso de uso**: `IncidentService.get_active_incidents_summary`

## Parámetros de consulta

| Parámetro | Tipo | Obligatorio | Descripción |
| --- | --- | --- | --- |
| `component` | `str` | no | Componente exacto y sensible a mayúsculas. Ausente, vacío o solo espacios → sin filtro |
| `reference_time` | `str` (ISO `YYYY-MM-DDTHH:MM:SS`) | no | Instante naive desde el que se mide el SLA. Si se omite, se usa el momento actual |

## Respuesta 200

```json
{
  "total_active": 3,
  "breached_count": 2,
  "incidents": [
    {
      "incident_id": "INC-A",
      "title": "Caída de la pasarela de pagos",
      "component": "payments-gateway",
      "severity": "P0",
      "status": "OPEN",
      "elapsed_minutes": 90,
      "requires_escalation": true
    }
  ]
}
```

- `incidents` se ordena por `incident_id` ascendente.
- `total_active` y `breached_count` se calculan sobre el conjunto resultante del filtro.
- Estado vacío (sin activos o sin coincidencias): `200 OK` con `{"total_active": 0, "breached_count": 0, "incidents": []}`. No es un error.

## Errores

| Situación | Respuesta |
| --- | --- |
| `reference_time` con zona horaria o formato inválido (FR-009) | `422 Unprocessable Entity` con detalle explicativo |
| Fecha anterior a la creación de un incidente evaluado (FR-013) | `422`, mismo tratamiento |
| Fallo de persistencia | `500` |

Esta sección es la fuente única de la semántica de errores; `summary-cli.md` y `quickstart.md` deben referirse a ella.

## Notas

- El endpoint no registra ni modifica incidentes.
- La respuesta es idéntica a la de la CLI (`summary-cli.md`) para los mismos parámetros.
- Los nombres de campos y la ruta son detalle técnico acordado en `spec.md > Clarifications`; los escenarios BDD permanecen en lenguaje de negocio.
