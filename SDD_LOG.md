# Bitácora de Desarrollo Guiado por Especificaciones — Semana 2 (`SDD_LOG.md`)
**Estudiante(s)**: `fabianvalderrama18`.  
**Fecha**: `2026-11-24`  
**Modelos Utilizados en OpenCode (Plan/Razonamiento vs. Build/Implementación)**: Se utilizó Codex como herramienta de asistencia para el análisis, la implementación y la verificación. No se utilizó OpenCode ni se realizó una comparación entre modelos de planificación e implementación.

Esta bitácora recoge las decisiones y los resultados de los hitos 003 y 004. Cada hito cuenta con especificación, plan, tareas y análisis de consistencia. Las referencias a `/speckit.*` corresponden a las etapas de la plantilla; la revisión se realizó sobre los documentos, sin ejecutar esos comandos.

---
## 1. Elicitación con `/speckit.clarify` y Auditoría con `/speckit.analyze`
### 1.1 Feature `003-incident-lifecycle-sla`
- **Ambigüedades y casos borde detectados con `/speckit.clarify`**: Durante la revisión del ciclo de vida se acordaron los siguientes criterios: (1) La búsqueda anterior por componente/severidad producía equivalencias incorrectas: ahora compara exclusivamente duplicate_group_key. (2) ESCALATION_REQUIRED cuenta como abierto; RESOLVED se excluye. (3) Un ID existente produce 409, evitando sobrescrituras secuenciales. (4) Los offsets se convierten a Bogotá; naive significa hora local de Bogotá. (5) RESOLVED sin resolved_at no inventa una fecha de cierre: evalúa hasta la referencia sin escalamiento. (6) Un tiempo anterior a creación se rechaza incluso para resueltos.
- **Hallazgos o validaciones de `/speckit.analyze` antes de implementar**: Revisión equivalente registrada en `specs/003-incident-lifecycle-sla/analysis.md`. Era necesario cambiar el puerto y migrar SQLite sin perder filas; se emitió ADR-005 antes de modificar código. Se mantuvo el contrato estricto del resumen H002 y del evaluador histórico. Se detectó que una BD en memoria creada por solicitud perdería los incidentes; la API conserva una conexión durante su vida y cierra al finalizar. Los cinco escenarios BDD tienen funciones test_bdd homónimas; casos borde adicionales se comprueban como regresiones.
### 1.2 Feature `004-postgres-container-runtime`
- **Ambigüedades y RNF aclarados antes de diseñar PostgreSQL/Compose**: (1) Salud significa SELECT 1 real, no un texto constante. (2) También un error al construir/conectar debe devolver 503 sin credenciales. (3) La URL ausente selecciona SQLite en memoria; esquemas no soportados se rechazan. (4) PostgreSQL limita establecimiento de conexión a tres segundos; esto no es un límite total de todas las consultas. (5) Fechas TEXT ISO permiten el mismo modelo temporal, pero validación temporal permanece en dominio/aplicación. (6) El volumen pertenece a db; api espera service_healthy y tiene su propio healthcheck. (7) La contraseña predeterminada de Compose es exclusivamente para desarrollo local; el despliegue debe definir POSTGRES_PASSWORD.

---
## 2. Comparación Crítica: SDD Manual (Iteración 1) vs. GitHub Spec Kit (Iteración 2 y Retos)
| Dimensión Comparada | SDD Manual (Iteración 1: `001`) | GitHub Spec Kit (Iteración 2 y Retos: `002`–`004`) |
| :--- | :--- | :--- |
| **Separación *QUÉ* vs. *CÓMO* vs. *TAREAS*** | Un documento facilita lectura inicial, pero puede mezclar contrato y decisiones. | spec, plan y tasks separan responsabilidades; en 003/004 se mantuvieron breves y enlazados al mismo comportamiento. |
| **Gestión de ambigüedades (`/speckit.clarify`)** | Depende de preguntas explícitas y de conservar sus respuestas. | Una etapa dedicada hace visibles ID repetido, offsets y significado de salud; el comando por sí solo no decide políticas correctas. |
| **Consistencia contra la Constitución (`/speckit.analyze`)** | Requiere contrastar manualmente reglas e implementación. | La auditoría detecta contradicciones de motor/puerto, pero las pruebas y Ruff aportan la verificación ejecutable. |
| **Riesgo de verbosidad / exceso de Markdown** | Menos archivos; riesgo de acumular un documento monolítico. | Más archivos; se evitaron repetir algoritmos y resultados en specs, plan y ADR. |

- **Análisis basado en MartinFowler.com (Birgitta Böckeler)**:
  1. El proyecto es **Spec-anchored**: conserva specs y sus pruebas para evolucionar el contrato. Es Spec-first por el orden de trabajo, pero no Spec-as-source porque el código se edita y revisa directamente; no se genera exclusivamente desde especificaciones.
  2. Para reducir revisión ciega, cada hito conserva pocos escenarios observables, un plan breve y tareas de cierre. Las decisiones estructurales se referencian por ADR. Los ejemplos temporales se comprueban con pytest y referencias fijas; no se acepta una narración como evidencia de ejecución.

Fuente consultada: [Birgitta Böckeler, Understanding Spec-Driven-Development](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html). La comparación de herramientas es un análisis de los artefactos y del artículo; no una medición experimental entre modelos.

---
## 3. *Commands* vs. *Agent Skills*, Arquitectura Hexagonal, ADRs y Uso de *Reasoning*
- **Diferencia entre *Commands* (`/speckit.*`) y *Agent Skills* (`hexagonal-architecture`, `bdd-acceptance`, `adr-writer`)**: Los comandos disparan etapas explícitas del flujo. Las skills aportan instrucciones especializadas cuando la tarea coincide con su descripción; su contenido se carga bajo demanda. Durante el desarrollo se revisaron las skills del proyecto y se incorporó y validó `adr-writer`. El orden ADR → Constitución → Hito evita especificar una dependencia prohibida: ADR-006 autoriza psycopg y actualiza la Constitución antes del plan de H004. El ADR histórico 004 se preserva; por eso la decisión de PostgreSQL solicitada con ese número ocupa 006, y el cambio de contrato ocupa 005.
- **Valor de la Arquitectura Hexagonal**: create y sla delegan en IncidentService tanto por REST como por CLI. IncidentRepositoryPort permite seleccionar SQLite/PostgreSQL sin importar drivers en aplicación. El dominio conserva triaje y calendario; solo se añadió normalización temporal pura. Una sonda temporal con import psycopg en dominio falló por TID251 y se retiró. Un futuro MCP debe invocar los mismos casos de uso.
- **Uso intencional de *Reasoning / Extended Thinking* en OpenCode**: El análisis se concentró en las etapas de aclaración, planificación y revisión de consistencia. Las decisiones que requirieron más atención fueron la identidad de los duplicados, la normalización temporal y la conservación de datos al cambiar de motor. La implementación de esquemas y la traducción entre HTTP/CLI y los casos de uso presentaron menos incertidumbre. Esta distinción permite identificar dónde convendría dedicar mayor esfuerzo de razonamiento; no se midieron diferencias de coste o tiempo entre modelos.

## Límites observados
- `docker compose -p incidentops-taller up --build -d` ejecutado con PostgreSQL real. Se verificaron creación, duplicados, SLA y CLI, persistencia tras reiniciar api/db y salud 503/200 al detener/arrancar db. Todas las operaciones del puerto se compararon con SQLite. Evidencias nuevas al final; se preserva el registro inicial del daemon apagado como antecedente.
- La consulta de duplicados y el guardado son operaciones separadas. No ofrecen deduplicación transaccional global ante altas simultáneas. El rechazo de IDs existentes está probado secuencialmente; se requiere una operación de creación atómica en el puerto para garantizarlo entre procesos concurrentes.
- La imagen fue construida y ejecutada. Las etiquetas de imágenes pueden cambiar de digest; este taller inicializa el esquema PostgreSQL desde el adaptador. Es una limitación de operación productiva, no una verificación pendiente de la entrega.
- SQLite sin DATABASE_URL es efímero. La CLI requiere una URL de archivo para conservar datos entre invocaciones.
- La suite emite una advertencia de deprecación de TestClient/httpx en las versiones instaladas; las aserciones pasan.

---
## 4. Evidencia de Verificación Determinista
- **Análisis estático de fronteras hexagonales (`uv run ruff check src/`)**:
```text
$ uv run ruff check src/
All checks passed!

exit_code=0
```

- **Salida completa de `uv run pytest -v`**:
```text
$ uv run pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.13.7, pytest-9.2.0, pluggy-1.7.0 -- /Users/alvaro.valderrama/Documents/Repo-Unal/taller_autonomo/.venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/alvaro.valderrama/Documents/Repo-Unal/taller_autonomo/week-1/starter-project
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.16.0
collecting ... collected 62 items

tests/test_sla.py::SLATests::test_all_severity_thresholds 
tests/test_sla.py::SLATests::test_all_severity_thresholds PASSED         [  1%]
tests/test_sla.py::SLATests::test_escalated_status_keeps_flag PASSED     [  3%]
tests/test_sla.py::SLATests::test_explicit_timezone_rejected PASSED      [  4%]
tests/test_sla.py::SLATests::test_fractional_minutes_accumulate_across_days PASSED [  6%]
tests/test_sla.py::SLATests::test_inputs_not_mutated PASSED              [  8%]
tests/test_sla.py::SLATests::test_invalid_interval_or_severity 
tests/test_sla.py::SLATests::test_invalid_interval_or_severity PASSED    [  9%]
tests/test_sla.py::SLATests::test_max_date_does_not_overflow PASSED      [ 11%]
tests/test_sla.py::SLATests::test_microsecond_after_deadline PASSED      [ 12%]
tests/test_sla.py::SLATests::test_one_second_beyond_sla PASSED           [ 14%]
tests/test_sla.py::SLATests::test_opening_closing_and_zero_duration 
tests/test_sla.py::SLATests::test_opening_closing_and_zero_duration PASSED [ 16%]
tests/test_sla.py::SLATests::test_random_intervals_against_minute_oracle 
tests/test_sla.py::SLATests::test_random_intervals_against_minute_oracle PASSED [ 17%]
tests/test_sla.py::SLATests::test_resolution_stops_clock_and_escalation PASSED [ 19%]
tests/test_sla.py::SLATests::test_resolved_incident_ignores_unused_reference_timezone PASSED [ 20%]
tests/test_sla.py::SLATests::test_resolved_status_without_timestamp PASSED [ 22%]
tests/test_spec_001_triage.py::test_bdd_caida_critica_http_502_en_pasarela_de_pagos PASSED [ 24%]
tests/test_spec_001_triage.py::test_bdd_cuenta_individual_bloqueada_mencionando_hoy PASSED [ 25%]
tests/test_spec_001_triage.py::test_bdd_entradas_vacias_o_con_solo_espacios[payload0] PASSED [ 27%]
tests/test_spec_001_triage.py::test_bdd_entradas_vacias_o_con_solo_espacios[payload1] PASSED [ 29%]
tests/test_spec_001_triage.py::test_bdd_paridad_en_cli PASSED            [ 30%]
tests/test_spec_001_triage.py::test_bdd_entradas_vacias_en_la_cli PASSED [ 32%]
tests/test_spec_002_summary.py::test_bdd_resumen_global_excluyendo_resueltos PASSED [ 33%]
tests/test_spec_002_summary.py::test_bdd_consulta_equivalente_por_cli PASSED [ 35%]
tests/test_spec_002_summary.py::test_bdd_resumen_filtrado_por_componente PASSED [ 37%]
tests/test_spec_002_summary.py::test_bdd_caso_vacio PASSED               [ 38%]
tests/test_spec_002_summary.py::test_repositorio_cumple_puerto PASSED    [ 40%]
tests/test_spec_002_summary.py::test_check_health PASSED                 [ 41%]
tests/test_spec_002_summary.py::test_operaciones_de_persistencia_preparacion_h003 PASSED [ 43%]
tests/test_spec_002_summary.py::test_reference_time_invalida_se_rechaza_http[2026-11-05] PASSED [ 45%]
tests/test_spec_002_summary.py::test_reference_time_invalida_se_rechaza_http[2026-11-05T09:00:00+00:00] PASSED [ 46%]
tests/test_spec_002_summary.py::test_reference_time_invalida_se_rechaza_http[2026-11-05T09:00:00Z] PASSED [ 48%]
tests/test_spec_002_summary.py::test_reference_time_invalida_se_rechaza_http[no-es-una-fecha] PASSED [ 50%]
tests/test_spec_002_summary.py::test_reference_time_invalida_se_rechaza_cli[2026-11-05] PASSED [ 51%]
tests/test_spec_002_summary.py::test_reference_time_invalida_se_rechaza_cli[2026-11-05T09:00:00+00:00] PASSED [ 53%]
tests/test_spec_002_summary.py::test_reference_time_anterior_a_creacion_se_rechaza_http PASSED [ 54%]
tests/test_spec_002_summary.py::test_reference_time_anterior_a_creacion_se_rechaza_cli PASSED [ 56%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_registro_inicial PASSED   [ 58%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_duplicado_abierto PASSED  [ 59%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_sla_habil PASSED          [ 61%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_errores_de_auditoria PASSED [ 62%]
tests/test_spec_003_lifecycle_sla.py::test_bdd_paridad_cli PASSED        [ 64%]
tests/test_spec_003_lifecycle_sla.py::test_invalid_create[title-] PASSED [ 66%]
tests/test_spec_003_lifecycle_sla.py::test_invalid_create[title-  ] PASSED [ 67%]
tests/test_spec_003_lifecycle_sla.py::test_invalid_create[raw_text- ] PASSED [ 69%]
tests/test_spec_003_lifecycle_sla.py::test_invalid_create[incident_id-] PASSED [ 70%]
tests/test_spec_003_lifecycle_sla.py::test_invalid_create[status-INVALID] PASSED [ 72%]
tests/test_spec_003_lifecycle_sla.py::test_invalid_create[created_at-2026-11-06] PASSED [ 74%]
tests/test_spec_003_lifecycle_sla.py::test_collision_and_timezone PASSED [ 75%]
tests/test_spec_003_lifecycle_sla.py::test_memory_lifetime PASSED        [ 77%]
tests/test_spec_003_lifecycle_sla.py::test_sqlite_migrates_existing_schema PASSED [ 79%]
tests/test_spec_004_runtime_health.py::test_bdd_salud_operativa PASSED   [ 80%]
tests/test_spec_004_runtime_health.py::test_bdd_salud_no_disponible PASSED [ 82%]
tests/test_spec_004_runtime_health.py::test_bdd_seleccion_de_motor PASSED [ 83%]
tests/test_spec_004_runtime_health.py::test_bdd_runtime_reproducible PASSED [ 85%]
tests/test_spec_004_runtime_health.py::test_connection_failure_is_503 PASSED [ 87%]
tests/test_spec_004_runtime_health.py::test_postgres_failure_uses_real_driver PASSED [ 88%]
tests/test_spec_004_runtime_health.py::test_closed_sqlite_health PASSED  [ 90%]
tests/test_triage.py::TriageRegressionTests::test_ids_do_not_control_results 
tests/test_triage.py::TriageRegressionTests::test_ids_do_not_control_results PASSED [ 91%]
tests/test_triage.py::TriageRegressionTests::test_normalization_preserves_all_cases 
tests/test_triage.py::TriageRegressionTests::test_normalization_preserves_all_cases PASSED [ 93%]
tests/test_triage.py::TriageRegressionTests::test_other_modules_import PASSED [ 95%]
tests/test_triage.py::TriageRegressionTests::test_other_payment_failure_does_not_invent_502 PASSED [ 96%]
tests/test_triage.py::TriageRegressionTests::test_unknown_requires_manual_review PASSED [ 98%]
tests/test_triage.py::TriageRegressionTests::test_urgency_does_not_control_results 
tests/test_triage.py::TriageRegressionTests::test_urgency_does_not_control_results PASSED [100%]

=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/fastapi/testclient.py:1
  /Users/alvaro.valderrama/Documents/Repo-Unal/taller_autonomo/.venv/lib/python3.13/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
============== 62 passed, 1 warning, 94 subtests passed in 3.58s ===============

exit_code=0
```

- **Evidencia de CLI Typer y containerización (`docker compose config` / `docker compose up --build`)**:
```text
$ uv run python -m src.adapters.inbound.cli create --title Cuenta bloqueada --raw-text Mi cuenta individual está bloqueada hoy y no puedo acceder --incident-id INC-DEMO --created-at 2026-11-06T17:00:00
{"incident_id":"INC-DEMO","severity":"P2","component":"auth-identity","rationale":"Bloqueo de una cuenta individual; requiere atención de identidad sin impacto generalizado.","recommended_team":"Security-IAM","duplicate_group_key":"auth-identity:account_lockout","consistency_ratio":1.0,"title":"Cuenta bloqueada","status":"OPEN","created_at":"2026-11-06T17:00:00","resolved_at":null,"is_duplicate":false,"duplicate_of":[]}
exit_code=0

$ uv run python -m src.adapters.inbound.cli sla --incident-id INC-DEMO --reference-time 2026-11-09T09:00:00
{"incident_id":"INC-DEMO","severity":"P2","elapsed_minutes":120,"allowed_minutes":480,"remaining_minutes":360,"is_breached":false,"requires_escalation":false}
exit_code=0

$ uv run python -m src.adapters.inbound.cli health
{"status": "ok", "database": "connected"}
exit_code=0

$ docker compose config -q

exit_code=0
$ docker info --format {{.ServerVersion}}

failed to connect to the docker API at unix:///Users/alvaro.valderrama/.docker/run/docker.sock; check if the path is correct and if the daemon is running: dial unix /Users/alvaro.valderrama/.docker/run/docker.sock: connect: no such file or directory

exit_code=1
```

Regresiones adicionales: demos de triaje (10 casos y regresiones), SLA (11 casos), unittest (20 pruebas), todas exitosas. Salidas conservadas en `evidencias/h003-h004/`.

## 5. Cierre de verificación real en contenedores

Se ejecutaron `docker compose -p incidentops-taller up --build -d`, `python3 scripts/verify_containers.py` y la comparación de repositorios dentro del contenedor API.

### runtime-real.txt
```text
GET /health -> 200 {'status': 'ok', 'database': 'connected'}
POST incidente -> 201, clasificación P2 persistida
POST equivalente -> 201, duplicado abierto detectado
SLA HTTP = CLI: 120 usados / 480 permitidos / 360 restantes
GET /health -> 200 {'status': 'ok', 'database': 'connected'}
Reinicio api + db: incidente y SLA conservados en volumen
GET /health -> 503 {'status': 'error', 'database': 'unavailable'}
GET /health -> 200 {'status': 'ok', 'database': 'connected'}
Recuperación de PostgreSQL verificada
NAME                       IMAGE                    COMMAND                  SERVICE   CREATED          STATUS                            PORTS
incidentops-taller-api-1   incidentops-taller-api   "uvicorn src.adapter…"   api       43 seconds ago   Up 3 seconds (health: starting)   127.0.0.1:8000->8000/tcp
incidentops-taller-db-1    postgres:16-alpine       "docker-entrypoint.s…"   db        44 seconds ago   Up 1 second (health: starting)    5432/tcp
```

### postgres-parity-real.txt
```text
PARIDAD REAL OK: save/upsert, get/ausente, duplicados/exclusión, activos y SELECT 1.
```

### containers-healthy.txt
```text
NAME                       IMAGE                                                                     COMMAND                  SERVICE   CREATED              STATUS                        PORTS
incidentops-taller-api-1   sha256:53060393387c3673c70550f4dc31849155048c7b86a6490ca9c5118f35125acf   "uvicorn src.adapter…"   api       About a minute ago   Up About a minute (healthy)   127.0.0.1:8000->8000/tcp
incidentops-taller-db-1    postgres:16-alpine                                                        "docker-entrypoint.s…"   db        About a minute ago   Up About a minute (healthy)   5432/tcp
```

