# Constitución Oficial de IncidentOps

- **Estado**: Vigente (ratificada)
- **Versión**: 1.0.0
- **Fecha**: 2026-11-21
- **Fundamentos**: `docs/adr/001-persistencia-sqlite-estandar.md`, `docs/adr/003-arquitectura-hexagonal.md`

## Preámbulo

Esta constitución fija las decisiones rectoras del producto y de la ingeniería de IncidentOps. Es normativa y prevalece sobre guías operativas y hábitos locales: `AGENTS.md` recoge los comandos y convenciones derivados, pero no puede contradecirla. Toda enmienda requiere un ADR aceptado con la plantilla MADR y el incremento de versión correspondiente.

## Artículo I — Núcleo determinista único

1. `src/domain/` es la única fuente de verdad de triaje, severidades y SLA, a través de `models.py`, `triage_rules.py` y `sla_calculator.py`.
2. Las reglas P0–P3, los plazos 24/7 y hábiles, el umbral de escalamiento del 75 %, los equipos y estados válidos y la clave de duplicados `component:symptom_category` se definen una sola vez en el dominio.
3. Ningún adaptador reimplementa, normaliza ni ajusta estas reglas: REST, CLI y un futuro MCP consumen el mismo resultado del caso de uso compartido. El `incident_id` no influye en la clasificación; el texto no reconocido se marca como P3 provisional con revisión humana. `consistency_ratio` se conserva por compatibilidad y no se presenta como confianza.
4. La lógica de dominio es pura y determinista: no depende de entrega, persistencia ni inferencia en tiempo de ejecución.

## Artículo II — Arquitectura Hexagonal estricta (ADR-003)

1. `src/domain/` contiene entidades y reglas puras. No importa `src.application`, `src.adapters` ni frameworks de entrega o persistencia (FastAPI, Pydantic, Typer, `sqlite3`); solo biblioteca estándar y otros módulos de `src.domain`.
2. `src/application/` contiene `ports.py`, con los puertos secundarios definidos mediante `typing.Protocol`, y `services.py`, con los casos de uso compartidos (`IncidentService.triage_incident`). La dependencia apunta de aplicación hacia dominio, nunca al revés.
3. `src/adapters/inbound/` aloja los adaptadores primarios: FastAPI para REST y Typer para CLI. Un futuro adaptador MCP se añade allí y delega en el servicio sin duplicar lógica.
4. `src/adapters/outbound/` aloja la persistencia intercambiable, configurable mediante `DATABASE_URL`. H001 es stateless; el cableado efectivo de `DATABASE_URL` se introduce con la persistencia en H003/H004, sin que la configuración llegue al dominio.
5. Las fronteras se verifican estáticamente con `uv run ruff check src/`: cualquier import del dominio hacia capas externas es una violación. Cambiar un puerto o el motor de persistencia exige ADR previo.

## Artículo III — Gobernanza técnica y calidad

1. Python >= 3.10 y entorno gestionado con `uv`; `uv.lock` es la fuente de verdad y se actualiza con `uv lock && uv sync` después de cualquier cambio de dependencias.
2. Stack de entrega: FastAPI + Pydantic v2 para REST, Typer para la CLI y `uvicorn` para servir la aplicación. `tiktoken` se reserva a la auditoría de contexto y nunca entra en el runtime.
3. Persistencia con SQLite3 estándar de la biblioteca estándar, sin ORMs pesados, según ADR-001, hasta que un ADR específico autorice otro motor.
4. Todo hito del roadmap se especifica en BDD (`Given / When / Then`) y se comprueba con `uv run pytest -v`. Las pruebas de aceptación son obligatorias para dar un hito por cerrado.
5. Documentación, comentarios, rationale y evidencias se escriben en español. Las evidencias de ejecuciones reales se preservan: no se reescriben para ajustarlas al código.

## Artículo IV — Enmiendas y precedencia

- Un cambio de regla de dominio, de puerto o de motor de persistencia requiere ADR aceptado y la consiguiente actualización de esta constitución.
- Ante cualquier conflicto rige el orden: Constitución > ADR > especificación > `AGENTS.md`.
