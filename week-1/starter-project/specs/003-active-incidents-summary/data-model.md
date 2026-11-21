# Data Model: Resumen de incidentes activos

## Entidades de dominio (existentes, sin cambios)

### `Incident` (`src/domain/models.py`)

| Campo | Tipo | Regla |
| --- | --- | --- |
| `incident_id` | `str` | Clave primaria; ordena el detalle de forma ascendente |
| `title` | `str` | Título mostrado en el detalle |
| `component` | `str` | Componente; coincide exactamente con el filtro (sensible a mayúsculas) |
| `severity` | `SeverityLevel` | `P0`/`P1`/`P2`/`P3`; debe existir política de SLA |
| `status` | `IncidentStatus` | Solo `OPEN` e `IN_PROGRESS` entran al resumen |
| `created_at` | `datetime` | Naive; inicio del cálculo de SLA |
| `resolved_at` | `datetime | None` | Naive; los activos no lo tienen; si existe, detiene el reloj |

### `SLARule` y `SLAEvaluation` (`src/domain/models.py`)

`SLARule` fija minutos permitidos, jornada 24/7 o hábil y umbral de escalamiento 0.75. `SLAEvaluation` es el resultado determinista de `evaluate_sla_status`: `elapsed_minutes`, `allowed_minutes`, `remaining_minutes`, `is_breached` (estricamente mayor que el plazo) y `requires_escalation` (desde el 75 %, persistente tras el vencimiento). ADR-002 rige estas reglas.

## Contrato de persistencia (`IncidentRepositoryPort`)

| Operación | Entrada | Salida | Semántica |
| --- | --- | --- | --- |
| `save_incident` | `Incident` | `None` | Alta o reemplazo por `incident_id`; usada para sembrar y por H003 |
| `get_incident` | `incident_id: str` | `Incident | None` | `None` si no existe |
| `find_open_duplicates` | `component: str`, `severity: SeverityLevel`, `created_after: datetime | None` | `list[Incident]` | Activos del mismo componente y severidad; orientado a H003, no usado en H002 |
| `list_active_incidents` | `component_filter: str | None = None` | `list[Incident]` | Solo `OPEN`/`IN_PROGRESS`, ordenados por identificador; `None` = sin filtro |
| `check_health` | — | `bool` | `True` si la conexión responde |

La conformidad es estructural (`@runtime_checkable`), no por herencia. Ver `contracts/repository-port.md`.

## Vista de aplicación (sin frameworks)

`src/application/services.py` define dos *dataclasses* internas, sin dependencias de entrega:

- `ActiveIncidentDetail`: `incident_id`, `title`, `component`, `severity`, `status`, `elapsed_minutes`, `requires_escalation`.
- `ActiveIncidentsSummary`: `total_active: int`, `breached_count: int`, `incidents: list[ActiveIncidentDetail]`.

El servicio construye estos objetos a partir de las entidades del repositorio y de `evaluate_sla_status`. `total_active` es el número de elementos del conjunto filtrado; `breached_count` suma `is_breached` sobre ese mismo conjunto.

## Esquemas de entrega (`src/adapters/inbound/api/schemas.py`)

- `ActiveIncidentItem` (Pydantic v2): refleja `ActiveIncidentDetail` con `model_config = ConfigDict(from_attributes=True)`.
- `ActiveIncidentsSummaryResponse` (Pydantic v2): `total_active`, `breached_count`, `incidents: list[ActiveIncidentItem]`.

La CLI serializa el mismo modelo, de modo que HTTP y CLI producen claves y orden idénticos (Constitución III).

## Persistencia (`src/adapters/outbound/sqlite_repository.py`)

Tablas heredadas:

- `sla_policies(severity TEXT PRIMARY KEY, max_resolution_minutes INTEGER NOT NULL, operates_24x7 INTEGER NOT NULL)`.
- `incidents(incident_id TEXT PRIMARY KEY, title TEXT NOT NULL, component TEXT NOT NULL, severity TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, resolved_at TEXT)`.

Fechas almacenadas como ISO naive (`datetime.isoformat()`); se reconstruyen con `datetime.fromisoformat()`. Índice nuevo: `idx_incidents_component_status ON incidents(component, status)`. Consulta de activos con `INNER JOIN sla_policies` para garantizar política conocida y evitar el N+1.

## Validaciones y reglas

1. Activos = `OPEN` o `IN_PROGRESS`; se excluyen `RESOLVED` y `ESCALATION_REQUIRED` aunque no tengan `resolved_at`.
2. Filtro ausente, vacío o solo espacios → sin filtro; presente → coincidencia exacta y sensible a mayúsculas.
3. `reference_time` naive en formato ISO; con zona o formato inválido → rechazo en el borde (`422` en HTTP, código `1` en CLI). Si se omite → `datetime.now()` aplicado por el servicio.
4. Fecha de referencia anterior a `created_at` de cualquier incidente evaluado → rechazada por el dominio (FR-013); el borde traduce el error a `422`/`1`. La semántica completa de errores se define en `contracts/summary-api.md`.
5. Caso vacío → respuesta válida con conteos a cero y lista vacía.
6. Orden determinista por `incident_id` ascendente.
7. `component_filter` ausente, vacío o solo espacios → `None`; la normalización la realiza el servicio, no los adaptadores.

## Transiciones de estado

H002 no cambia estados: solo consume el estado ya persistido. La creación, el cierre y el escalamiento pertenecen a H003. `resolved_at` no interviene en la selección de activos, pero el dominio lo respeta en `evaluate_sla_status`.

## Dataset canónico de aceptación

**Fuente única de los valores de este hito.** `reference_time` canónico: `2026-11-05T09:00:00` (fecha local naive, jueves). Las fechas de creación se derivan restando los minutos transcurridos de ese instante; INC-D se cierra en el propio instante de referencia.

| ID | Componente | Severidad | Estado | `created_at` | `resolved_at` | Minutos transcurridos | Incumplimiento |
| --- | --- | --- | --- | --- | --- | --- | --- |
| INC-A | payments-gateway | P0 | OPEN | 2026-11-05T07:30:00 | — | 90 | sí |
| INC-B | payments-gateway | P1 | IN_PROGRESS | 2026-11-05T05:40:00 | — | 200 | no |
| INC-C | auth-identity | P1 | OPEN | 2026-11-05T04:00:00 | — | 300 | sí |
| INC-D | reporting-api | P3 | RESOLVED | 2026-11-05T08:30:00 | 2026-11-05T09:00:00 | 30 | excluido |

Sin filtro: `total_active=3`, `breached_count=2`. Filtro `payments-gateway`: `2` y `1`. Filtro `frontend-ui`: `0`, `0`, `incidents=[]`.
