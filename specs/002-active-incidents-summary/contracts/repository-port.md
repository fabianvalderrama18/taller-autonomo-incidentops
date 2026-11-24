# Contrato — `IncidentRepositoryPort`

**Ubicación**: `src/application/ports.py`
**Tipo**: `typing.Protocol` con `@runtime_checkable`
**Implementación prevista**: `src.adapters.outbound.sqlite_repository.SQLiteIncidentRepository`
**Construcción**: exclusivamente mediante `src.adapters.outbound.factory.create_incident_repository`

## Firmas

```python
def save_incident(self, incident: Incident) -> None: ...
def get_incident(self, incident_id: str) -> Incident | None: ...
def find_open_duplicates(
    self, component: str, severity: SeverityLevel, created_after: datetime | None = None
) -> list[Incident]: ...
def list_active_incidents(self, component_filter: str | None = None) -> list[Incident]: ...
def check_health(self) -> bool: ...
```

## Semántica

- `save_incident`: inserción o reemplazo por `incident_id`. No valida reglas de negocio.
- `get_incident`: devuelve la entidad de dominio o `None`.
- `find_open_duplicates`: activos (`OPEN`/`IN_PROGRESS`) del mismo componente y severidad, opcionalmente desde `created_after`. Preparado para H003; H002 no lo invoca.
- `list_active_incidents`: devuelve solo entidades activas, ordenadas por identificador. `component_filter=None` significa sin filtro; un valor se compara de forma exacta y sensible a mayúsculas. No devuelve métricas de SLA.
- `check_health`: `True` si la conexión responde; `False` ante fallo.

## Reglas de implementación

- La conformidad es **estructural**: la clase concreta no hereda del `Protocol`, para evitar falsos positivos por los *stubs* heredados.
- El puerto no expone `sqlite3`, SQL ni formatos de transporte. Los `datetime` son naive en todos los métodos.
- El repositorio legado `IncidentRepository` conserva su comportamiento didáctico y deja de declarar herencia del puerto; no se usa desde la aplicación.

## Verificación

`tests/test_spec_002_summary.py` incluye una prueba no BDD que construye el repositorio con la factory y afirma:

```python
assert isinstance(repository, IncidentRepositoryPort)
```

Además, `uv run ruff check src/` impide que `src/application/` importe adaptadores o drivers de base de datos (TID251) y que cualquier capa use imports relativos hacia padres (TID252).
