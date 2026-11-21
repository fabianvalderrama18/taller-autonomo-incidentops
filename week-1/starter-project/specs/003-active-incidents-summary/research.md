# Research: Resumen de incidentes activos

**Fecha**: 2026-11-21
**Fuentes**: `spec.md`, `.specify/memory/constitution.md`, ADR-001/002/003 y estado real de `src/` y `pyproject.toml`.

## R1 — Propiedad de la lógica SLA y firmas del puerto

**Decision**: el puerto expone operaciones de persistencia, no cálculos de negocio:

```python
@runtime_checkable
class IncidentRepositoryPort(Protocol):
    def save_incident(self, incident: Incident) -> None: ...
    def get_incident(self, incident_id: str) -> Incident | None: ...
    def find_open_duplicates(
        self, component: str, severity: SeverityLevel, created_after: datetime | None = None
    ) -> list[Incident]: ...
    def list_active_incidents(self, component_filter: str | None = None) -> list[Incident]: ...
    def check_health(self) -> bool: ...
```

`list_active_incidents` devuelve entidades `Incident` del dominio. `IncidentService.get_active_incidents_summary` aplica `evaluate_sla_status` a cada entidad y construye el agregado. `check_health` ejecuta `SELECT 1` y devuelve `bool`. `find_open_duplicates` queda declarado para H003 (no se invoca en H002). El método heredado `get_active_incidents_summary` se retira del puerto: el cálculo de SLA no puede vivir en el adaptador. Este cambio de puerto está autorizado por ADR-004 (aceptado) y por la Constitución v1.2.0; debe registrarse antes de modificar `src/application/ports.py`.

Ni `SQLiteIncidentRepository` ni el repositorio legado deben heredar explícitamente del `Protocol`: los *stubs* heredados harían que `isinstance(repo, IncidentRepositoryPort)` diera falso positivo. La conformidad es estructural y se comprueba con `isinstance` sobre el objeto real.

**Rationale**: la Constitución I y ADR-002 hacen del dominio la única fuente de reglas de SLA; si el adaptador devolviera diccionarios con `is_breached` o `requires_escalation`, la regla se duplicaría en SQL y en Python. Las entidades de dominio mantienen el límite limpio y permiten que el mismo caso de uso alimente REST y CLI.

**Alternatives considered**: (a) conservar `get_active_incidents_summary` en el puerto y dejar el SLA en SQLite — rechazado, rompe el núcleo determinista; (b) devolver `dict[str, Any]` desde el repositorio — rechazado, pierde tipado y mezcla capas; (c) heredar del `Protocol` — rechazado por los falsos positivos de `runtime_checkable`.

## R2 — Persistencia optimizada y destino del repositorio legado

**Decision**: crear `src/adapters/outbound/sqlite_repository.py` con `SQLiteIncidentRepository`, que conserva el esquema `incidents` + `sla_policies` y añade el índice compuesto `idx_incidents_component_status ON incidents(component, status)`. La consulta de activos es una única sentencia con `INNER JOIN sla_policies`, filtro parametrizado (`? IS NULL OR i.component = ?`) y `ORDER BY i.incident_id`. El `JOIN` garantiza que solo se listan incidentes con política de SLA conocida, en una sola vuelta a la base de datos; los valores de la política **no** se usan para calcular el SLA.

`src/adapters/outbound/factory.py` pasa a construir `SQLiteIncidentRepository` resolviendo `DATABASE_URL` con default `sqlite:///:memory:` (recortando el prefijo `sqlite:///`). El módulo legado `incident_repository.py`, el shim `src/incident_repository.py`, el benchmark y las evidencias de Semana 1 permanecen sin cambios: el escaneo completo y el N+1 son artefactos pedagógicos documentados en `AGENTS.md`.

**Rationale**: el requerimiento pide la versión optimizada «heredada de Semana 1» como una extracción, no como una reescritura del artefacto didáctico. Un módulo nuevo permite comparar ambos enfoques y preservar las evidencias ya entregadas. El índice compuesto sirve al filtro por componente; el `INNER JOIN` evita la consulta N+1 a `sla_policies`.

**Alternatives considered**: (a) refactorizar `incident_repository.py` in situ — rechazado, destruye el benchmark y las evidencias; (b) cambiar a otro motor — rechazado, ADR-001 fija SQLite estándar; (c) añadir un ORM — rechazado, ADR-001; (d) calcular el SLA en SQL con la tabla de políticas — rechazado, duplica reglas del dominio.

## R3 — Representación de «sin filtro» y validación de `reference_time`

**Decision**: el puerto usa `component_filter: str | None = None`. El servicio normaliza un valor ausente, vacío o compuesto solo por espacios a `None`; los adaptadores entregan el parámetro de transporte sin aplicar reglas propias. El repositorio aplica coincidencia exacta y sensible a mayúsculas. `reference_time` se valida en el borde: formato ISO `YYYY-MM-DDTHH:MM:SS`, sin zona horaria; fecha inválida o con zona produce `422` en HTTP y código `1` en CLI (FR-009). El servicio acepta `reference_time: datetime | None = None` y aplica `datetime.now()` cuando se omite, de modo que el valor por defecto existe en un solo lugar. Una fecha anterior a `created_at` la rechaza el dominio (FR-013) y el borde traduce ese error. Los totales se calculan después del filtro y el detalle se ordena por identificador, como exige la spec. La semántica de errores se centraliza en `contracts/summary-api.md`.

**Rationale**: `None` es la única representación inequívoca de «sin filtro» y evita confundir `""` o `"   "` con un componente real. Validar en el borde mantiene la aplicación libre de formatos de transporte; el servicio recibe ya un `datetime`, por lo que REST y CLI no pueden divergir en la interpretación. Centralizar la normalización en el servicio evita dos copias en los adaptadores y cumple la Constitución III. El default en el servicio evita duplicar `datetime.now()` en dos adaptadores.

**Alternatives considered**: (a) cadena vacía como centinela en el puerto — rechazado, ambiguo; (b) pasar `reference_time` como `str` al servicio — rechazado, acopla aplicación a ISO; (c) validar solo en HTTP y confiar en la CLI — rechazado, rompe paridad; (d) inyectar un reloj — rechazado, añade complejidad innecesaria en H002; los escenarios BDD siempre pasan un instante explícito.

## R4 — Ruff jerárquico con `extend` sin perder `TID251`

**Decision**: `pyproject.toml` conserva `[tool.ruff.lint] select = ["E4", "E7", "E9", "F", "TID"]` y `ban-relative-imports = "parents"`. Se elimina el `per-file-ignores` amplio `"src/adapters/**" = ["TID251"]`, porque Ruff lo propaga a los archivos hijos aunque estos usen `extend` y silencia sus propias prohibiciones. Quedan ignores estrechos solo para los shims heredados y `tests/**`. Los cuatro archivos jerárquicos usan `extend`: `src/domain/ruff.toml` y `src/application/ruff.toml` con `../../pyproject.toml`; `src/adapters/inbound/ruff.toml` y `src/adapters/outbound/ruff.toml` con `../../../pyproject.toml`. Cada uno declara su propia tabla `banned-api`: el de `outbound` permite `sqlite3` y `src.application` porque son dependencias legítimas de la persistencia, pero prohíbe frameworks de entrega, ORMs y `src.adapters.inbound`. TID252 sigue activo por herencia. El archivo de `outbound` debe existir antes de eliminar el ignore global.

La verificación incluye sondas temporales que deben fallar: dominio → `src.application`, aplicación → `sqlite3`, inbound → `sqlite3` y → `src.adapters.outbound.incident_repository`, e import relativo con `..`. Las sondas se eliminan después. No se usan `# noqa`.

**Rationale**: el requerimiento pide `extend` hacia `pyproject.toml`, pero la experiencia previa mostró que el ignore global dejaba sin efecto las prohibiciones de `inbound`. Reducir el ignore a los archivos heredados permite cumplir ambos objetivos simultáneamente.

**Alternatives considered**: (a) mantener `inbound/ruff.toml` autónomo, como hoy — funciona pero incumple el requerimiento de `extend`; (b) eliminar el ignore global sin crear `outbound/ruff.toml` — rechazado, `ruff check src/` fallaría en los módulos de persistencia; (c) añadir `# noqa` en los adaptadores — prohibido por la Constitución V; (d) abandonar TID251 en inbound — debilita la frontera.

## R5 — Aislamiento de base de datos en pruebas

**Decision**: `tests/conftest.py` incorpora fixtures frescas por prueba: un repositorio en memoria creado a través de `src.adapters.outbound.factory` con `database_url="sqlite:///:memory:"`, un conjunto canónico de 4 incidentes sembrado mediante `save_incident` dentro de la propia fixture, y clientes `TestClient`/`CliRunner` construidos sobre esa instancia. `create_app()` construirá el servicio y el repositorio al invocarse (no a nivel de módulo), y la CLI creará el repositorio dentro del comando `summary`, de modo que `DATABASE_URL` (o el argumento explícito de la factory) gobierne cada ejecución. No hay BD global ni semilla compartida.

Las 4 funciones `test_bdd_*` de `tests/test_spec_002_summary.py` ejercitan los escenarios de la spec. Pruebas separadas y no BDD comprueban `isinstance(repo, IncidentRepositoryPort)`, el rechazo de `reference_time` inválido, con zona o anterior a `created_at` en ambos canales (FR-009, FR-013, SC-005) y `check_health`. La verificación de rendimiento de SC-006 se ejecuta aparte sobre `SQLiteIncidentRepository` con 10.000 registros y se registra en `evidencias/`; no se introduce en la suite BDD ni se reescriben las evidencias del repositorio legado.

**Rationale**: la skill `bdd-acceptance` exige almacenamiento aislado y mapeo 1:1 escenario → `test_bdd_*`. Construir el repositorio en el borde (y no en el import) evita que un cambio de `DATABASE_URL` en una prueba contaminen a las demás.

**Alternatives considered**: (a) archivo SQLite temporal compartido — rechazado, estado entre pruebas; (b) servicio global a nivel de módulo — rechazado, ignora la configuración por prueba; (c) insertar filas con SQL directo en la prueba — rechazado, el puerto existe precisamente para eso.

## R6 — Patrones de integración HTTP/CLI y verificación

**Decision**: ambos adaptadores llaman a `IncidentService.get_active_incidents_summary` y serializan el mismo agregado con los modelos Pydantic `ActiveIncidentItem` y `ActiveIncidentsSummaryResponse`; la CLI emite el JSON de ese mismo modelo para garantizar claves y orden idénticos. La verificación completa del hito es: `uv run ruff check src/`, `uv run pytest -v`, demos heredadas (`src.triage_rules`, `src.sla_calculator`), `uv run python -m unittest discover -s tests`, smoke HTTP/CLI con el dataset canónico, benchmark de SC-006 sobre `SQLiteIncidentRepository` con 10.000 registros y `git diff --check`. El benchmark del módulo legado se ejecuta por separado y no sustituye esta medición.

**Rationale**: la Constitución III exige paridad observable; un único modelo de respuesta evita que un canal cambie de forma sin el otro. Las demos y el benchmark heredados se ejecutan aparte para no alterar evidencias ni convertir el artefacto didáctico en una prueba de regresión.

**Alternatives considered**: serializadores independientes por canal — rechazado, permite divergencia silenciosa.

## Resumen de clarificaciones resueltas

| Clarificación de `plan.md` | Resolución |
| --- | --- |
| Firmas del puerto y propiedad del SLA | R1 |
| Persistencia optimizada sin destruir el artefacto legado | R2 |
| Representación de «sin filtro» y validación de `reference_time` | R3 |
| `extend` jerárquico sin perder `TID251` | R4 |
| Aislamiento de BD en pruebas | R5 |
| Integración y patrones de verificación | R6 |
| Gobernanza del cambio de puerto (ADR-004 y Constitución v1.2.0) | R1 |
| Cobertura de FR-009/FR-013 y verificación de SC-006 | R5, R6 |
