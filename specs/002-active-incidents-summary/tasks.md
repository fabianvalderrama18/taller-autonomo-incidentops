---
description: "Task list for feature implementation"
---

# Tasks: Resumen de incidentes activos

**Input**: Design documents from `/specs/002-active-incidents-summary/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: incluidos porque la spec define 4 escenarios BDD y el plan solicita explícitamente `tests/test_spec_002_summary.py`.

**Organization**: tareas agrupadas por historia de usuario para permitir implementación y verificación independientes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede ejecutar en paralelo (archivos distintos, sin dependencias de tareas incompletas)
- **[Story]**: historia de usuario (US1, US2, US3), solo en las fases de usuario
- Las rutas son relativas a ``

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: ajustar la configuración compartida sin añadir dependencias.

- [X] T001 Verificar que H002 no requiere dependencias nuevas y confirmar bloqueo de versiones en `pyproject.toml` y `uv.lock`
- [X] T002 [P] Confirmar que ADR-004 está aceptado en `docs/adr/004-puerto-persistencia-incidentes.md` y que `.specify/memory/constitution.md` está en v1.2.0 antes de tocar el puerto
- [X] T003 [P] Reducir `per-file-ignores` en `pyproject.toml`: eliminar `"src/adapters/**" = ["TID251"]` y conservar ignores estrechos para shims y `tests/**` (decisión `research.md` R4)
- [X] T004 [P] Crear `src/adapters/outbound/ruff.toml` con `extend = "../../../pyproject.toml"` y `banned-api` que permita `sqlite3` y `src.application` pero prohíba frameworks de entrega, ORMs y `src.adapters.inbound`; TID252 queda heredado
- [X] T005 [P] Verificar y consolidar `extend = "../../pyproject.toml"` y reglas TID251/TID252 en `src/domain/ruff.toml`
- [X] T006 [P] Verificar y consolidar `extend = "../../pyproject.toml"` y reglas TID251/TID252 en `src/application/ruff.toml`
- [X] T007 [P] Añadir `extend = "../../../pyproject.toml"` y reglas TID251/TID252 en `src/adapters/inbound/ruff.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: contrato de persistencia, repositorio optimizado, factory y fixtures. Ninguna historia puede empezar antes de cerrar esta fase.

**⚠️ CRITICAL**: no iniciar US1/US2/US3 hasta completar T018.

- [X] T008 Ampliar `IncidentRepositoryPort` en `src/application/ports.py` con `save_incident`, `get_incident`, `find_open_duplicates`, `list_active_incidents` y `check_health`; retirar `get_active_incidents_summary` (ADR-004, `contracts/repository-port.md`; depende de T002)
- [X] T009 [P] Crear `SQLiteIncidentRepository` en `src/adapters/outbound/sqlite_repository.py` con esquema e índice compuesto, según `data-model.md → incidents.incident_id`, `data-model.md → incidents.title`, `data-model.md → incidents.component`, `data-model.md → incidents.severity`, `data-model.md → incidents.status`, `data-model.md → incidents.created_at`, `data-model.md → incidents.resolved_at`, `data-model.md → sla_policies.severity`, `data-model.md → sla_policies.max_resolution_minutes` y `data-model.md → sla_policies.operates_24x7`
- [X] T010 Implementar `save_incident`, `get_incident` y `check_health` en `src/adapters/outbound/sqlite_repository.py`, respetando `data-model.md → Incident.incident_id`, `data-model.md → Incident.title`, `data-model.md → Incident.created_at` y `data-model.md → Incident.resolved_at`. `get_incident` y `check_health` son preparación H003, sin FR/SC propio en H002 (depende de T009)
- [X] T011 Implementar `list_active_incidents` en `src/adapters/outbound/sqlite_repository.py` con `INNER JOIN sla_policies`, índice `(component, status)`, filtro parametrizado y orden por identificador, según `data-model.md → Incident.status`, `data-model.md → Incident.component`, `data-model.md → Incident.severity` y regla 6 de `data-model.md` (depende de T009)
- [X] T012 Implementar `find_open_duplicates` en `src/adapters/outbound/sqlite_repository.py`, según `data-model.md → Incident.status`, `data-model.md → Incident.component`, `data-model.md → Incident.severity` y `data-model.md → Incident.created_at`. Operación de preparación H003, sin criterio de aceptación en H002 (depende de T009)
- [X] T013 Actualizar `src/adapters/outbound/factory.py` para resolver `DATABASE_URL` con default `sqlite:///:memory:` y devolver `SQLiteIncidentRepository` como `IncidentRepositoryPort`
- [X] T014 [P] Retirar la herencia explícita del `Protocol` en `src/adapters/outbound/incident_repository.py`, preservando íntegramente su comportamiento didáctico y el benchmark
- [X] T015 Verificar `uv run ruff check src/` y ejecutar las sondas temporales de TID251/TID252 descritas en `quickstart.md`, eliminando cada sonda después (depende de T003, T004, T005, T006, T007)
- [X] T016 Crear fixtures aisladas en `tests/conftest.py`: repositorio en memoria vía factory, dataset canónico sembrado con `save_incident` usando las fechas de `data-model.md > Dataset canónico de aceptación` y clientes `TestClient`/`CliRunner` frescos por prueba
- [X] T017 Crear `tests/test_spec_002_summary.py` con la comprobación de cumplimiento de puerto (`isinstance(repository, IncidentRepositoryPort)`), los soportes para las 4 funciones `test_bdd_*` y las pruebas no BDD de `reference_time` inválida, con zona o anterior a `created_at` en ambos canales (FR-009, FR-013, SC-005) y de `check_health`; ejecutarla antes de implementar para confirmar que falla
- [X] T018 [P] Verificar que `src/domain/sla_calculator.py` y `SLA_POLICY_TABLE` no se modifican, conservando `data-model.md → SLARule.max_resolution_minutes`, `data-model.md → SLARule.operates_24x7`, `data-model.md → SLARule.escalation_threshold_ratio`, `data-model.md → SLAEvaluation.allowed_minutes` y `data-model.md → SLAEvaluation.remaining_minutes`

**Checkpoint**: base lista; las tres historias pueden comenzar.

---

## Phase 3: User Story 1 — Ver el estado de los incidentes activos (Priority: P1) 🎯 MVP

**Goal**: resumen global con total, incumplimientos y detalle de los activos, excluyendo resueltos y escalados.

**Independent Test**: con el dataset canónico de `data-model.md`, la consulta HTTP global devuelve 3 activos, 2 incumplimientos y 3 items en el detalle; no aparece INC-D.

### Tests for User Story 1 ⚠️

> Escribir primero y confirmar que fallan antes de implementar.

- [X] T019 [US1] Escribir `test_bdd_resumen_global_excluyendo_resueltos` en `tests/test_spec_002_summary.py`, con docstring `Given/When/Then` y aserciones sobre la respuesta HTTP del dataset canónico (depende de T016, T017)

### Implementation for User Story 1

- [X] T020 [P] [US1] Definir las vistas de aplicación `ActiveIncidentDetail` y `ActiveIncidentsSummary` en `src/application/services.py`, según `data-model.md → ActiveIncidentDetail.incident_id`, `data-model.md → ActiveIncidentDetail.title`, `data-model.md → ActiveIncidentDetail.component`, `data-model.md → ActiveIncidentDetail.severity`, `data-model.md → ActiveIncidentDetail.status`, `data-model.md → ActiveIncidentDetail.elapsed_minutes`, `data-model.md → ActiveIncidentDetail.requires_escalation`, `data-model.md → ActiveIncidentsSummary.total_active`, `data-model.md → ActiveIncidentsSummary.breached_count` y `data-model.md → ActiveIncidentsSummary.incidents`
- [X] T021 [US1] Implementar `IncidentService.get_active_incidents_summary(component_filter, reference_time)` en `src/application/services.py`: normalizar `component_filter` ausente, vacío o solo espacios a `None`, aplicar `datetime.now()` si `reference_time` es `None`, delegar el SLA a `evaluate_sla_status` y respetar las reglas 1, 4, 5 y 7 de `data-model.md`, sin redefinir `data-model.md → SLARule.max_resolution_minutes`, `data-model.md → SLARule.operates_24x7` ni `data-model.md → SLARule.escalation_threshold_ratio` y consumiendo `data-model.md → SLAEvaluation.elapsed_minutes`, `data-model.md → SLAEvaluation.allowed_minutes`, `data-model.md → SLAEvaluation.remaining_minutes`, `data-model.md → SLAEvaluation.is_breached` y `data-model.md → SLAEvaluation.requires_escalation` (depende de T008, T011, T020)
- [X] T022 [P] [US1] Definir `ActiveIncidentItem` y `ActiveIncidentsSummaryResponse` en `src/adapters/inbound/api/schemas.py`, según `data-model.md → ActiveIncidentItem.incident_id`, `data-model.md → ActiveIncidentItem.title`, `data-model.md → ActiveIncidentItem.component`, `data-model.md → ActiveIncidentItem.severity`, `data-model.md → ActiveIncidentItem.status`, `data-model.md → ActiveIncidentItem.elapsed_minutes`, `data-model.md → ActiveIncidentItem.requires_escalation`, `data-model.md → ActiveIncidentsSummaryResponse.total_active`, `data-model.md → ActiveIncidentsSummaryResponse.breached_count` y `data-model.md → ActiveIncidentsSummaryResponse.incidents`
- [X] T023 [US1] Añadir `GET /api/v1/incidents/summary` en `src/adapters/inbound/api/app.py`: construir el repositorio vía `src.adapters.outbound.factory`, inyectarlo en `IncidentService`, parsear `reference_time` en el borde con `422` para fechas inválidas, con zona o anteriores a `created_at` (FR-009, FR-013), y devolver el esquema de `contracts/summary-api.md` (depende de T013, T021, T022)
- [X] T024 [US1] Verificar US1 de forma aislada en `tests/test_spec_002_summary.py`: ejecutar `test_bdd_resumen_global_excluyendo_resueltos`, `uv run ruff check src/` y comprobar FR-011 comparando el número de filas antes y después de la consulta

**Checkpoint**: US1 funciona y se valida sin depender de la CLI ni del filtro.

---

## Phase 4: User Story 2 — Obtener el mismo resumen desde la terminal (Priority: P2)

**Goal**: el subcomando `summary` entrega exactamente el mismo JSON que el canal HTTP.

**Independent Test**: con el mismo dataset e instante de referencia, `CliRunner` y `TestClient` producen objetos JSON idénticos y la CLI termina con código `0`.

### Tests for User Story 2 ⚠️

- [X] T025 [US2] Escribir `test_bdd_consulta_equivalente_por_cli` en `tests/test_spec_002_summary.py`, comparando el stdout de `CliRunner` con la respuesta HTTP y comprobando el código de salida (depende de T016, T017)

### Implementation for User Story 2

- [X] T026 [US2] Añadir el comando `summary` con `--component` y `--reference-time` en `src/adapters/inbound/cli.py`, creando el repositorio dentro del comando vía factory, parseando `reference_time` con código `1` ante fechas inválidas, con zona o anteriores a `created_at`, y serializando `ActiveIncidentsSummaryResponse` según `contracts/summary-cli.md` (depende de T013, T021, T022)
- [X] T027 [US2] Verificar US2 de forma aislada en `tests/test_spec_002_summary.py`: ejecutar `test_bdd_consulta_equivalente_por_cli`, confirmar que no hay lógica de SLA ni normalizaciones propias en `src/adapters/inbound/cli.py`, comprobar FR-011 y validar que los casos de error producen la misma semántica que HTTP

**Checkpoint**: US1 y US2 son independientemente funcionales y observables.

---

## Phase 5: User Story 3 — Reducir el resumen a un componente (Priority: P3)

**Goal**: filtrar por componente con totales recalculados y respuesta vacía válida cuando no hay coincidencias.

**Independent Test**: filtrando por `payments-gateway` se obtienen 2 activos y 1 incumplimiento; filtrando por `frontend-ui` se obtiene `200` con ceros y lista vacía.

### Tests for User Story 3 ⚠️

- [X] T028 [US3] Escribir `test_bdd_resumen_filtrado_por_componente` y `test_bdd_caso_vacio` en `tests/test_spec_002_summary.py`, con docstrings `Given/When/Then`, aserciones sobre totales y detalle vacío, y una comprobación de que un componente compuesto solo por espacios equivale a sin filtro (depende de T016, T017)

### Implementation for User Story 3

- [X] T029 [US3] Dejar en `src/adapters/inbound/api/app.py` y `src/adapters/inbound/cli.py` únicamente la traducción de parámetros de transporte y la validación de formato de `reference_time`, conforme a `data-model.md → Incident.component` y las reglas 2, 3 y 4 de `data-model.md`; la normalización de `component` y el default de fecha ya están en T021 (depende de T021, T023, T026)
- [X] T030 [US3] Verificar US3 de forma aislada: ejecutar los dos escenarios filtrados, confirmar orden por identificador y que el caso vacío devuelve `200`/JSON válido en ambos canales

**Checkpoint**: las tres historias funcionan de forma independiente.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: cierre documental y verificación integral del hito.

- [X] T031 [P] Actualizar `AGENTS.md` con los comandos de H002, el repositorio optimizado, `src/adapters/outbound/ruff.toml` y el default `DATABASE_URL`
- [X] T032 [P] Confirmar que `src/adapters/outbound/incident_repository.py`, `src/incident_repository.py`, `CONTEXT_LOG.md` y `evidencias/` no se reescribieron
- [X] T033 [P] Verificar el mapeo 1:1 de los 4 escenarios de `spec.md` a las 4 funciones `test_bdd_*` en `tests/test_spec_002_summary.py`, con docstrings `Given/When/Then`
- [X] T034 [P] Ejecutar el benchmark de SC-006 sobre `src/adapters/outbound/sqlite_repository.py` con 10.000 registros y una sola llamada, registrando el resultado en `evidencias/h002-summary-benchmark.md` sin sobrescribir evidencias anteriores
- [X] T035 Ejecutar la validación completa de `specs/002-active-incidents-summary/quickstart.md`: Ruff, `pytest -v`, demos heredadas, `unittest`, benchmark, smoke HTTP/CLI y `git diff --check`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias; T002–T007 son paralelos entre sí. T003 y T004 deben completarse antes de T015.
- **Foundational (Phase 2)**: T008 depende de T002 (ADR-004); T009 precede a T010, T011 y T012 por compartir archivo; T015 depende de T003–T007; bloquea todas las historias hasta T018.
- **User Stories (Phase 3+)**: dependen de T018. T019, T021 y T023 son secuenciales dentro de US1; T020 y T022 son paralelos entre sí. US2 y US3 reutilizan el caso de uso y el esquema; sus pruebas comparten `tests/test_spec_002_summary.py`, por lo que se ejecutan en orden.
- **Polish (Phase 6)**: depende de las tres historias; T031–T034 son paralelos, T035 va al final.

### User Story Dependencies

- **US1 (P1)**: sin dependencias de otras historias; entrega el MVP.
- **US2 (P2)**: reutiliza el caso de uso y el esquema de US1; verificable por separado con `CliRunner`.
- **US3 (P3)**: reutiliza el caso de uso; verificable por separado con dos consultas filtradas.

### Within Each User Story

- Prueba primero (debe fallar) → vistas/esquemas → servicio → adaptador → verificación aislada.
- Sin cambios en `src/domain/`: las reglas de SLA ya están implementadas y T018 lo confirma.
- Los adaptadores solo traducen transporte; la normalización de negocio y el default de fecha viven en `IncidentService`.

### Parallel Opportunities

- Setup: T002, T003, T004, T005, T006, T007.
- Foundational: T009, T014 y T018; T010, T011 y T012 continúan sobre el archivo creado por T009.
- US1: T020 y T022 (archivos distintos).
- Tras T018, las tres historias podrían asignarse a personas distintas; las pruebas comparten archivo y conviene serializarlas.
- Polish: T031, T032, T033 y T034.

---

## Parallel Example: User Story 1

```bash
# Ejecutar juntas las tareas marcadas [P] de US1:
Task: "T020 Definir vistas de aplicación en src/application/services.py"
Task: "T022 Definir esquemas Pydantic en src/adapters/inbound/api/schemas.py"

# La prueba T019 se escribe antes y se ejecuta en solitario para confirmar que falla.
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1 y Phase 2 (base obligatoria, incluido ADR-004 y `outbound/ruff.toml`).
2. Completar Phase 3 (US1).
3. **DETENER Y VALIDAR**: ejecutar `test_bdd_resumen_global_excluyendo_resueltos`, Ruff y la comprobación de FR-011.
4. Mostrar el endpoint HTTP con el dataset canónico.

### Incremental Delivery

1. Base lista → US1 → validar → MVP.
2. US2 → validar paridad y semántica de errores → demo por terminal.
3. US3 → validar filtro y caso vacío → demo completa.
4. Cada etapa conserva las anteriores sin reimplementar reglas.

### Parallel Team Strategy

1. Equipo completo cierra Setup y Foundational.
2. Desarrollador A: US1 · Desarrollador B: US2 · Desarrollador C: US3.
3. Integrar pruebas de forma serializada por el archivo compartido.

---

## Notes

- `[P]` implica archivos distintos y sin dependencias pendientes.
- Las citas `data-model.md → Entidad.campo` son la fuente canónica de restricciones; no se duplican en las tareas.
- No se usan `# noqa` para eludir TID251/TID252.
- No se reescriben evidencias, demos ni el benchmark didáctico; la medición de SC-006 es nueva.
- Los 4 escenarios BDD deben mapear 1:1 con los 4 escenarios de la spec; FR-009/FR-013 se verifican con pruebas de adaptador separadas.
- La semántica de errores se define en `contracts/summary-api.md`; los valores canónicos, en `data-model.md > Dataset canónico de aceptación`.
