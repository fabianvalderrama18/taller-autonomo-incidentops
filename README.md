# IncidentOps — Taller autónomo SDD

Entrega de los hitos **003 y 004**. La aplicación ejecutable y todos los entregables están en esta raíz.
La carpeta remota `week-1/` conserva el antecedente de la práctica; la entrega vigente es esta raíz.

## Verificación

```sh
uv sync --frozen
uv run ruff check src/
uv run pytest -v
uv run python -m unittest discover -s tests -v
docker compose config -q
docker compose -p incidentops-taller up --build -d
python3 scripts/verify_containers.py
docker compose -p incidentops-taller exec -T api python - < scripts/verify_repository_parity.py
```

Resultados: 62 pruebas y 94 subpruebas aprobadas; Ruff correcto. Imagen construida,
API y PostgreSQL saludables, persistencia tras reinicio, paridad de repositorios y
salud 503/200 ante caída/recuperación de la base verificados realmente.

## Entregables

- [Bitácora y evidencias reales](SDD_LOG.md).
- [Roadmap](docs/ROADMAP.md), [Constitución histórica](docs/constitution.md) y [Constitución vigente](.specify/memory/constitution.md).
- [H001](specs/001-triage-endpoint-manual.md), [H002](specs/002-active-incidents-summary/), [H003](specs/003-incident-lifecycle-sla/) y [H004](specs/004-postgres-container-runtime/).
- Skills en [.opencode/skills/](.opencode/skills/) y comandos en [.opencode/commands/](.opencode/commands/).
- [ADR de PostgreSQL solicitado como 004](docs/adr/004-persistencia-postgresql-y-runtime-contenedores.md): corresponde al registro inmutable ADR-006 porque el número 004 ya existía para el puerto. Ambos antecedentes se conservan explícitamente.

## Uso local

```sh
export DATABASE_URL=sqlite:///incidentops.db
uv run python -m src.adapters.inbound.cli create --title 'Cuenta bloqueada' --raw-text 'Mi cuenta individual está bloqueada hoy' --incident-id INC-DEMO --created-at 2026-11-06T17:00:00
uv run python -m src.adapters.inbound.cli sla --incident-id INC-DEMO --reference-time 2026-11-09T09:00:00
uv run python -m src.adapters.inbound.cli health
uv run uvicorn src.adapters.inbound.api.app:app --reload
```

API: POST `/api/v1/incidents`, GET `/api/v1/incidents/{incident_id}/sla`, GET `/health`.
Creación devuelve 201, entrada inválida 422, ID existente 409, incidente ausente 404.
H003 acepta offsets y los normaliza a Bogotá; H002 conserva su entrada naive.
La clave de duplicados incluye OPEN, IN_PROGRESS y ESCALATION_REQUIRED, excluye RESOLVED.
Sin DATABASE_URL se usa SQLite efímero en memoria. Compose usa PostgreSQL dedicado.

La contraseña de Compose es para desarrollo local; definir POSTGRES_PASSWORD en otro entorno.
`docker compose -p incidentops-taller down` detiene los servicios conservando el volumen.
Las limitaciones de concurrencia están declaradas en la bitácora; no se promete deduplicación transaccional global.
