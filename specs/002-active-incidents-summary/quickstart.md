# Quickstart — Validación de H002

Esta guía describe cómo **verificar** el hito, no cómo implementarlo. Los detalles de código están en `plan.md`, `data-model.md` y `contracts/`.

## Prerrequisitos

- Ejecutar todos los comandos desde ``.
- Entorno sincronizado: `uv lock && uv sync` tras cualquier cambio de dependencias (H002 no añade dependencias).
- Python >= 3.10.

## 1. Fronteras hexagonales

```bash
uv run ruff check src/
```

Esperado: `All checks passed!`. `src/adapters/outbound/ruff.toml` debe existir antes de retirar el ignore global de TID251. Las sondas temporales de dominio → aplicación, aplicación → `sqlite3`, inbound → `sqlite3`/repositorio concreto, outbound → framework de entrega e imports relativos `..` deben fallar con TID251/TID252 y se eliminan después de comprobarlo.

## 2. Aceptación BDD

```bash
uv run pytest -v
```

Esperado: los 4 escenarios de `spec.md` mapeados a `test_bdd_*` en `tests/test_spec_002_summary.py` pasan, junto con las pruebas de puerto, de fecha inválida/con zona/anterior a `created_at` (FR-009, FR-013, SC-005) y de `check_health`; se conservan los 5 escenarios de H001. El instante y las fechas del dataset se toman de `data-model.md > Dataset canónico de aceptación`: `reference_time=2026-11-05T09:00:00`.

## 3. Pruebas heredadas y demos

```bash
uv run python -m src.triage_rules
uv run python -m src.sla_calculator
uv run python -m unittest discover -s tests -v
uv run python -m src.incident_repository --records 10000 --iterations 1
```

Esperado: demos y 20 pruebas stdlib en verde; el benchmark sigue mostrando el anti-patrón deliberado del módulo legado. No se reescriben evidencias.

## 4. Smoke de CLI

```bash
uv run python -m src.adapters.inbound.cli summary --component payments-gateway --reference-time 2026-11-05T09:00:00
uv run python -m src.adapters.inbound.cli summary --component frontend-ui --reference-time 2026-11-05T09:00:00
```

Esperado: el primer comando imprime el resumen del dataset sembrado; el segundo imprime `{"total_active": 0, "breached_count": 0, "incidents": []}` con código `0`. Sin semilla, cualquier consulta devuelve el resumen vacío. Una fecha con zona (p. ej. `2026-11-05T09:00:00+00:00`) o anterior a `created_at` termina con código `1`; la semántica completa está en `contracts/summary-api.md`.

## 5. Smoke de HTTP

```bash
uv run uvicorn src.adapters.inbound.api.app:app --reload
curl 'http://127.0.0.1:8000/api/v1/incidents/summary?component=payments-gateway&reference_time=2026-11-05T09:00:00'
curl 'http://127.0.0.1:8000/api/v1/incidents/summary?component=frontend-ui&reference_time=2026-11-05T09:00:00'
```

Esperado: `200` con el mismo JSON que la CLI para los mismos parámetros. Sin semilla, `DATABASE_URL` usa `sqlite:///:memory:` y ambas consultas devuelven `{"total_active": 0, "breached_count": 0, "incidents": []}`; el dataset canónico se siembra en las pruebas a través de `DATABASE_URL`. Una fecha con zona o anterior a `created_at` produce `422`, según `contracts/summary-api.md`.

## 6. Rendimiento de SC-006

```bash
uv run python -m src.adapters.outbound.sqlite_repository --benchmark --records 10000 --iterations 1
```

Esperado: el resumen completo se entrega en una sola llamada al repositorio optimizado, sin el escaneo completo ni el patrón N+1 del módulo legado. Registrar la medición en `evidencias/h002-summary-benchmark.md` sin sobrescribir evidencias anteriores.

## 7. Cierre

```bash
git diff --check
```

Esperado: sin salida. Los contratos de respuesta y del puerto están en `contracts/`; el dataset canónico y sus resultados esperados, en `data-model.md`.
