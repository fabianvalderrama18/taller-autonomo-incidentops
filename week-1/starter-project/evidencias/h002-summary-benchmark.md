# Evidencia H002 — Rendimiento del resumen de incidentes activos (SC-006)

**Fecha**: 2026-11-21
**Entorno**: `uv run` desde `week-1/starter-project/`, Python 3.15, SQLite3 estándar en memoria.
**Criterio**: SC-006 — una sola petición entrega el resumen completo con hasta 10.000 incidentes registrados.

## Comando ejecutado (repositorio optimizado)

```bash
uv run python -m src.adapters.outbound.sqlite_repository --benchmark --records 10000 --iterations 1
```

## Salida real

```text
Sembrando 10000 incidentes en SQLite en memoria...
=== Resultado del Benchmark (Después de Refactorizar) ===
Incidentes activos encontrados para 'payments-gateway': 800
Tiempo total (1 ejecuciones sobre 10000 filas): 2.33 ms
Promedio por consulta: 2.33 ms
Diagnóstico: `list_active_incidents` usa el índice (component, status) y un INNER JOIN a sla_policies en una sola consulta, sin N+1.
```

La consulta se resuelve en una única llamada a `SQLiteIncidentRepository.list_active_incidents`, con filtro parametrizado, `INNER JOIN sla_policies` e índice compuesto `(component, status)`. El SLA no se calcula en SQL: el dominio sigue siendo la única fuente de reglas.

## Contraste con el artefacto didáctico (medición separada)

```bash
uv run python -m src.incident_repository --records 10000 --iterations 1
```

```text
Sembrando 10000 incidentes en SQLite en memoria...
=== Resultado del Benchmark (Antes de Refactorizar) ===
Incidentes activos encontrados para 'payments-gateway': 800
Tiempo total (1 ejecuciones sobre 10000 filas): 20.32 ms
Promedio por consulta: 20.32 ms
Diagnóstico: `get_active_incidents_summary` escanea toda la tabla en memoria y ejecuta consultas N+1 por cada fila activa.
```

Ambas mediciones devuelven los mismos 800 activos. La versión optimizada tarda 2,33 ms frente a 20,32 ms del anti-patrón intencional. No se han reescrito las evidencias heredadas ni el módulo `src/adapters/outbound/incident_repository.py`.
