# Contrato CLI — Resumen de incidentes activos

**Comando**: `summary`
**Adaptador**: `src/adapters/inbound/cli.py`
**Caso de uso**: `IncidentService.get_active_incidents_summary`

## Sintaxis

```text
summary [--component <componente>] [--reference-time <YYYY-MM-DDTHH:MM:SS>]
```

| Opción | Tipo | Obligatoria | Descripción |
| --- | --- | --- | --- |
| `--component` | `str` | no | Componente exacto y sensible a mayúsculas; ausente o vacío → sin filtro |
| `--reference-time` | `str` ISO naive | no | Instante de referencia; por defecto, momento actual |

## Salida

Éxito: código `0` y en stdout el mismo JSON que el endpoint HTTP, con `total_active`, `breached_count` e `incidents` (`incident_id`, `title`, `component`, `severity`, `status`, `elapsed_minutes`, `requires_escalation`).

Sin activos o sin coincidencias: código `0` y `{"total_active": 0, "breached_count": 0, "incidents": []}`.

Error: mensaje en stderr y código `1` cuando `reference_time` sea inválida, tenga zona horaria o sea anterior a la creación de un incidente (FR-009, FR-013). La semántica completa se define en `contracts/summary-api.md`.

## Ejemplos

```text
$ python -m src.adapters.inbound.cli summary --component payments-gateway --reference-time 2026-11-05T09:00:00
{"total_active": 2, "breached_count": 1, "incidents": [...]}
```

```text
$ python -m src.adapters.inbound.cli summary --component frontend-ui --reference-time 2026-11-05T09:00:00
{"total_active": 0, "breached_count": 0, "incidents": []}
```

## Notas

- El repositorio se crea dentro del comando desde `src.adapters.outbound.factory`, leyendo `DATABASE_URL` (default `sqlite:///:memory:`). La CLI no importa `sqlite3` ni repositorios concretos.
- `DATABASE_URL` con prefijo `sqlite:///` se recorta en la factory.
- El subcomando `summary` sustituye la nomenclatura preliminar `active-incidents` del borrador `002`.
