# Implementation Plan: Resumen de incidentes activos

**Branch**: `002-active-incidents-summary` | **Date**: 2026-11-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-active-incidents-summary/spec.md`

**Note**: este archivo fue generado por `/speckit.plan`; describe el diseño técnico y la estrategia de verificación, no la ejecución del código.

## Summary

H002 añade una consulta de solo lectura sobre el conjunto de incidentes activos (`OPEN` e `IN_PROGRESS`), con totales, incumplimientos de SLA y detalle por incidente, filtrable por componente. La lógica de SLA sigue siendo exclusiva de `src.domain.sla_calculator`; el nuevo caso de uso en `src.application.services` orquesta el repositorio a través de `IncidentRepositoryPort`, y los adaptadores HTTP y CLI solo traducen la misma respuesta. La ampliación del puerto está autorizada por ADR-004, aceptado antes de tocar `src/application/ports.py`. La persistencia optimizada vive en un módulo nuevo (`src/adapters/outbound/sqlite_repository.py`) y se construye desde `factory.py` leyendo `DATABASE_URL` (default `sqlite:///:memory:`), preservando el repositorio legado como artefacto didáctico.

## Technical Context

**Language/Version**: Python >= 3.10 (`requires-python` en `pyproject.toml`).

**Primary Dependencies**: FastAPI + Pydantic v2 (HTTP), Typer (CLI), uvicorn (servidor), `sqlite3` de biblioteca estándar (persistencia); pytest + httpx + Ruff como dependencias de desarrollo. `tiktoken` queda relegado a la auditoría de contexto.

**Storage**: SQLite3 estándar sin ORM (ADR-001). `DATABASE_URL` se resuelve en `src/adapters/outbound/factory.py`, con default `sqlite:///:memory:`; prefijo `sqlite:///` recortado en el borde.

**Testing**: `uv run pytest -v` con `TestClient` (FastAPI) y `CliRunner` (Typer); 4 funciones `test_bdd_*` mapeadas 1:1 a los escenarios de la spec, más pruebas de puerto, de validación de fecha (FR-009/FR-013) y de salud del repositorio. SC-006 se verifica aparte con un benchmark de 10.000 registros sobre `SQLiteIncidentRepository`. Fronteras con `uv run ruff check src/`.

**Target Platform**: servicio HTTP local y terminal, sin contenedores ni despliegue en H002.

**Project Type**: web-service + CLI sobre un hexágono (`domain` → `application` → `adapters`).

**Performance Goals**: entregar el resumen completo en una sola petición con conjuntos de hasta 10.000 incidentes (SC-006), mediante una única consulta SQL con `INNER JOIN sla_policies` e índice compuesto `(component, status)`, sin el escaneo completo ni el patrón N+1 del módulo legado.

**Constraints**: `datetime` naive (sin zona); incumplimiento solo si se supera estrictamente el plazo; escalamiento desde el 75 % y persistente tras el vencimiento; totales calculados después del filtro; detalle ordenado por identificador; caso vacío es `200`/JSON válido, no error; sin ORM, sin reglas de negocio en adaptadores, sin `# noqa` para eludir Ruff; `src/adapters/outbound/ruff.toml` debe existir antes de retirar el ignore global de TID251; documentación y evidencias en español.

**Scale/Scope**: 4 incidentes canónicos de aceptación; hasta 10.000 registros sintéticos para la verificación de escala; dos canales de entrega (HTTP y CLI). Quedan fuera de alcance el registro vía HTTP/CLI, el ciclo de vida, los duplicados, la paginación y la autenticación.

**Clarificaciones técnicas** (marcadas como `NEEDS CLARIFICATION` al iniciar el plan y resueltas en Fase 0):

- ~~NEEDS CLARIFICATION~~ → R1: firmas de `save_incident`, `get_incident`, `find_open_duplicates` y `check_health`, y qué capa calcula el SLA del resumen.
- ~~NEEDS CLARIFICATION~~ → R2: cómo introducir la persistencia optimizada sin destruir el repositorio legado que sostiene el benchmark y las evidencias de Semana 1.
- ~~NEEDS CLARIFICATION~~ → R3: representación de «sin filtro» y lugar donde se valida `reference_time`.
- ~~NEEDS CLARIFICATION~~ → R4: cómo mantener `extend` jerárquico en los `ruff.toml` sin que los `per-file-ignores` globales silencien `TID251`.
- ~~NEEDS CLARIFICATION~~ → R5: aislamiento de base de datos y *fixtures* para las pruebas BDD sin estado compartido.

Ninguna clarificación queda sin resolver: `research.md` las cierra con decisión, justificación y alternativas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción | Gate verificable | Estado |
| --- | --- | --- |
| I. Núcleo determinista único | `evaluate_sla_status` es la única fuente de `elapsed_minutes`, `is_breached` y `requires_escalation`; `src/domain/` sigue sin imports externos | PASS (condicionado a R1) |
| II. Arquitectura Hexagonal estricta | ADR-004 aceptado antes de tocar el puerto; implementación en `src/adapters/outbound/`; inbound usa `factory`; `DATABASE_URL` resuelto solo en el borde | PASS (ADR-004; condicionado a R1, R2) |
| III. Paridad de adaptadores primarios | HTTP y CLI invocan el mismo `IncidentService.get_active_incidents_summary` y serializan la misma estructura; la normalización vive en la aplicación | PASS (Constitución v1.2.0; condicionado a R3) |
| IV. Gobernanza tecnológica | `uv`/`uv.lock`, FastAPI/Pydantic v2, Typer, SQLite3 sin ORM; sin dependencias nuevas en runtime | PASS |
| V. Verificación obligatoria | `uv run ruff check src/` limpio con TID251/TID252 y `outbound/ruff.toml`; 4 escenarios BDD → 4 `test_bdd_*`; pruebas de adaptador para FR-009/FR-013; sin `noqa` | PASS (condicionado a R4, R5) |
| Preservación de evidencias | El benchmark y los shims heredados no se reescriben; el nuevo código es aditivo | PASS (condicionado a R2) |

**Resultado del gate**: el único conflicto detectado fue el cambio de puerto sin ADR previo; quedó resuelto con ADR-004 y la Constitución v1.2.0 antes de la Fase 0. R4 añade `src/adapters/outbound/ruff.toml` para que retirar el ignore global no rompa `ruff check src/`. Las restantes condiciones se convierten en decisiones de Fase 0 y se verifican de nuevo al cierre de Fase 1. ADR-001, ADR-002, ADR-003 y ADR-004 cubren las decisiones estructurales.

### Re-evaluación tras Fase 1

| Principio | Estado post-diseño | Evidencia en el diseño |
| --- | --- | --- |
| I | PASS | El adaptador devuelve entidades `Incident`; el servicio llama a `evaluate_sla_status`; el `INNER JOIN` solo garantiza integridad de la política, no calcula reglas (`research.md` R1, `data-model.md`) |
| II | PASS | ADR-004 aceptado; `IncidentRepositoryPort` ampliado; `SQLiteIncidentRepository` lo implementa estructuralmente; `factory.py` es el único punto de construcción (`contracts/repository-port.md`) |
| III | PASS | Ambos adaptadores comparten el caso de uso y el contrato de respuesta; la normalización de `component` está en la aplicación; la CLI y la HTTP difieren solo en transporte (`contracts/summary-api.md`, `contracts/summary-cli.md`) |
| IV | PASS | Sin cambios de dependencias; la persistencia sigue siendo `sqlite3` estándar |
| V | PASS | 4 escenarios ↔ 4 `test_bdd_*`; pruebas de puerto y de fecha (FR-009/FR-013) fuera de los BDD; Ruff jerárquico con cuatro `extend`, incluido `outbound`; benchmark de SC-006 separado (`research.md` R4/R5/R6) |
| Evidencias | PASS | `src/adapters/outbound/incident_repository.py` y `src/incident_repository.py` permanecen intactos como artefactos didácticos |

## Project Structure

### Documentation (this feature)

```text
specs/002-active-incidents-summary/
├── spec.md              # fuente de aceptación (entrada)
├── plan.md              # este archivo
├── research.md          # Fase 0: decisiones técnicas
├── data-model.md        # Fase 1: entidades y reglas
├── contracts/
│   ├── summary-api.md       # contrato HTTP
│   ├── summary-cli.md       # contrato CLI
│   └── repository-port.md   # contrato del puerto secundario
├── quickstart.md        # Fase 1: guía de validación ejecutable
├── checklists/
│   └── requirements.md  # checklist de calidad de la spec
└── tasks.md             # Fase 2 (/speckit.tasks); creado tras el plan
```

### Source Code (repository root)

```text

├── pyproject.toml                       # [tool.ruff.lint]; per-file-ignores estrechos
├── src/
│   ├── domain/                          # sin cambios de reglas
│   │   ├── models.py
│   │   ├── triage_rules.py
│   │   ├── sla_calculator.py
│   │   └── ruff.toml                    # extend = "../../pyproject.toml"
│   ├── application/
│   │   ├── ports.py                     # IncidentRepositoryPort ampliado (5 métodos)
│   │   ├── services.py                  # + get_active_incidents_summary
│   │   └── ruff.toml                    # extend = "../../pyproject.toml"
│   └── adapters/
│       ├── inbound/
│       │   ├── api/
│       │   │   ├── app.py               # + GET /api/v1/incidents/summary
│       │   │   └── schemas.py           # + ActiveIncidentItem / ActiveIncidentsSummaryResponse
│       │   ├── cli.py                   # + comando summary
│       │   └── ruff.toml                # extend = "../../../pyproject.toml"
│       └── outbound/
│           ├── factory.py               # DATABASE_URL -> SQLiteIncidentRepository
│           ├── sqlite_repository.py     # NUEVO: INNER JOIN + índice compuesto
│           ├── incident_repository.py   # legado intacto (benchmark didáctico)
│           └── ruff.toml                # NUEVO: permite sqlite3 solo en persistencia
├── tests/
│   ├── conftest.py                      # + fixtures aisladas de BD y datos canónicos
│   ├── test_spec_001_triage.py          # sin cambios
│   └── test_spec_002_summary.py         # NUEVO: 4 test_bdd_* + pruebas de puerto/fecha
├── evidencias/
│   └── h002-summary-benchmark.md        # NUEVO: medición de SC-006 (10.000 registros)
└── data/sample_incidents.json           # solo lectura
```

**Structure Decision**: se mantiene el único paquete `src` del proyecto (``), sin subproyectos. La persistencia optimizada se añade como módulo nuevo en la capa outbound y el repositorio legado se conserva, porque el benchmark y las evidencias de Semana 1 dependen de su comportamiento intencionalmente lento. La gobernanza del cambio de puerto vive en `docs/adr/004-puerto-persistencia-incidentes.md`. No se introducen carpetas `contract/`, `integration/` ni `unit/` en `tests/`: el patrón existente es un archivo de spec por hito.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Sin violaciones que justificar. No se requiere tabla de complejidad.

## Plan de ejecución

- **Fase 0** — `research.md`: resolver las clarificaciones técnicas y fijar seis decisiones con alternativas evaluadas.
- **Fase 1** — `data-model.md`, `contracts/*.md` y `quickstart.md`: modelo de datos, contratos de los dos canales y del puerto, y guía de validación. Reevaluar el Constitution Check (hecho arriba).
- **Fase 2** — `/speckit.tasks`: generar `tasks.md`. No forma parte de este comando.
