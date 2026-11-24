# AGENTS.md — IncidentOps (taller ISIA, semana 1)

## Scope
- La entrega vigente está en la raíz del repositorio (`src/`, `tests/`, `docs/`, `specs/`). `week-1/` remoto se conserva como antecedente histórico de la base main; no es el punto de ejecución de esta entrega. Other top-level dirs (`Lab_CI-CD/`, `mattermost/`, `lab2/`, `taller3/`, etc.) are untracked local material; `mattermost/` has its own AGENTS.md and is unrelated.
- Python 3.10+, one `src` package, `uv`/`uv.lock`. Runtime now uses FastAPI/Pydantic v2, uvicorn and Typer; `tiktoken` is only for the context-audit tool. Dev deps are pytest/httpx/ruff. Ruff enforces the hexagonal boundaries; verification = BDD acceptance + boundary check + legacy demos + unittest. `.specify/memory/constitution.md` (v1.2.0) is the normative Spec Kit constitution; `docs/constitution.md` is the historical base. `docs/adr/001-persistencia-sqlite-estandar.md` records the SQLite-without-ORM decision and `docs/adr/004-puerto-persistencia-incidentes.md` records the repository-port change.

## Commands — run from the repository root
- `uv lock && uv sync` after dependency changes; `uv.lock` is the source of truth. `uv run --offline ...` only works once the new wheels are cached; older evidence was produced offline.
- `uv run pytest -v` — mandatory BDD acceptance scenarios: 5 in `tests/test_spec_001_triage.py` and 4 in `tests/test_spec_002_summary.py` (HTTP + CLI), plus adapter/port checks.
- `uv run ruff check src/` — static check of hexagonal boundaries with hierarchical `ruff.toml` files (TID251/TID252); probes must fail and be deleted.
- `uv run uvicorn src.adapters.inbound.api.app:app --reload` — triage API at `POST /api/v1/incidents/triage`; summary API at `GET /api/v1/incidents/summary?component=&reference_time=`.
- `uv run python -m src.adapters.inbound.cli triage --incident-id INC-1001 --raw-text "..."` — CLI, JSON on stdout.
- `uv run python -m src.adapters.inbound.cli summary [--component ...] [--reference-time ...]` — resumen de activos, el mismo JSON que HTTP; fecha ISO naive, `422`/código `1` si es inválida, con zona o anterior a `created_at`.
- `uv run python -m src.triage_rules` — legacy triage demo, asserts 10 expected cases + regressions, exits 1 on failure.
- `uv run python -m src.sla_calculator` — SLA demo, 11 asserted cases.
- `uv run python -m unittest discover -s tests -v` — legacy 20 stdlib tests; still green via compatibility shims.
- `uv run python -m src.context_audit --symbol classify_incident_report` (also `evaluate_sla_status`, or `--compare-formats`) — token accounting. "LSP" here is AST simulation, not a real LSP server; exact counts require `uv run` so tiktoken is importable. Its patterns still scan `src/*.py`, so nested modules are no longer counted; don't rerun or overwrite evidence.
- `uv run python -m src.incident_repository --records 10000 --iterations 1` — optional integration benchmark of the legacy artifact. Its full-table scan and N+1 queries are intentional teaching artifacts, not bugs to fix for this assignment.
- `uv run python -m src.adapters.outbound.sqlite_repository --benchmark --records 10000 --iterations 1` — SC-006 benchmark of the optimized repository (single `INNER JOIN` query + `(component, status)` index); results in `evidencias/h002-summary-benchmark.md`.

## Code invariants
- `src/domain/models.py` is the public contract (old `src/models.py` is a shim): keep signatures and dataclass field order. `TriageResult.consistency_ratio` is legacy compatibility only, not a confidence measure.
- Triage classifies from report text only: normalize accents/case/whitespace, never branch on `incident_id`; `EXPECTED` in `src/domain/triage_rules.py` is verification-only. Unknown text gets provisional P3 requiring manual review; canonical payment key is `payments-gateway:payment_http_502` (a shared key does not imply equal severity or common root cause).
- SLA: P0 60 min and P1 240 min continuous; P2 480 and P3 1440 business minutes, Mon–Fri [08:00,18:00), no holidays. Naive datetimes only (tz-aware rejected); `resolved_at` stops the clock and suppresses escalation; breach only when strictly past the deadline; escalation starts at 75% and persists after breach; `remaining_minutes` may go negative; evaluation never mutates state or notifies.
- Hexagonal layout (ADR-003, ADR-004): pure rules in `src/domain/`, `IncidentService` in `src/application/services.py` (triage and `get_active_incidents_summary`), `IncidentRepositoryPort` in `src/application/ports.py` (5 persistence operations, structural conformance), inbound REST/CLI in `src/adapters/inbound/` (no DB drivers or concrete repository imports; use `src.adapters.outbound.factory`), repository in `src/adapters/outbound/` implementing that port (old paths are shims). Hierarchical `ruff.toml` files refine the per-layer bans, including `src/adapters/outbound/ruff.toml` for SQLite. H001 is stateless (no DB calls); H002 reads active incidents via `SQLiteIncidentRepository` with an `INNER JOIN` and `(component, status)` index. `DATABASE_URL` defaults to `sqlite:///:memory:` and is resolved only in `factory.py`; tests point it to an isolated file per case. A future MCP adapter must call the service, not duplicate rules.
- GenAI appears only in the workflow/prompt documents, never at runtime; don't add LLM dependencies to `src/`.

## Deliverables
- `CONTEXT_LOG.md`, `PROMPT_*.md`, `docs/adr/002-calculo-sla-horario-habil.md`, and `evidencias/` are graded records of real runs and model comparisons. Preserve them rather than overwriting snapshots to match new code; when reporting results, distinguish expected values from commands actually executed. `specs/001-triage-endpoint-manual.md` is the H001 acceptance source and `specs/002-active-incidents-summary/spec.md` is the H002 source.
- Docs, comments, rationale strings, and evidence are in Spanish; keep that language when editing.


## Actualización operativa H003/H004 — 2026-11-24
- Constitución vigente 2.0.0; ADR-005 cambia contrato de duplicados y normalización temporal H003; ADR-006 autoriza SQLite/PostgreSQL dual sin ORM. Estas reglas reemplazan las descripciones previas de las mismas operaciones.
- `find_open_duplicates(duplicate_group_key, exclude_incident_id=None)` busca OPEN, IN_PROGRESS y ESCALATION_REQUIRED; nunca por severidad/componente.
- `create_repository` (alias compatible `create_incident_repository`) selecciona motor. psycopg solo está permitido en outbound. `repository_scope` cierra SQLite; PostgreSQL usa conexiones por operación.
- `IncidentService.create_incident`, `evaluate_incident_sla` y `check_health` sirven a REST/CLI. H003 acepta offsets y normaliza a Bogotá. El evaluador legado y H002 conservan validación naive.
- Verificación: `uv run pytest -v`, `uv run ruff check src/`, `docker compose config -q`. Nuevos escenarios en test_spec_003_lifecycle_sla.py y test_spec_004_runtime_health.py. Evidencias en `evidencias/h003-h004/`; informe raíz `SDD_LOG.md`.
- CLI: `create --title ... --raw-text ... [--incident-id ... --created-at ... --status ...]`, `sla --incident-id ... [--reference-time ...]`, `health`. Para persistir entre comandos, establecer DATABASE_URL=sqlite:///incidentops.db.
- PostgreSQL y contenedores verificados realmente el 2026-11-24: evidencia runtime-real.txt, postgres-parity-real.txt y containers-healthy.txt. Scripts repetibles en scripts/.
