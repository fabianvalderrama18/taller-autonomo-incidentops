<!--
SYNC IMPACT REPORT
Version change: 1.0.0 → 1.1.0 → 1.2.0
Modified principles:
  - "Núcleo determinista único": ampliado con reglas verificables de triaje y SLA.
  - "Arquitectura Hexagonal": renombrado a "Arquitectura Hexagonal estricta"; se
    explicita ports.py, services.py, factory y DATABASE_URL.
  - v1.2.0: "Paridad de adaptadores primarios" generaliza el caso de uso compartido
    más allá de `triage_incident`; "Fronteras y decisiones registradas" añade ADR-004.
Added sections:
  - III. Paridad de adaptadores primarios
  - IV. Gobernanza tecnológica y dependencias
  - V. Verificación obligatoria
  - Fronteras y decisiones registradas
  - Flujo de trabajo y calidad
Removed sections: ninguna
Follow-up TODOs: ninguno
Nota: el scaffold previo de Spec Kit contenía solo marcadores de plantilla, sin
valores propios del proyecto que fuera necesario conservar.
-->

# IncidentOps Constitution

## Core Principles

### I. Núcleo determinista único

`src/domain/` es la única fuente de verdad de triaje y SLA, mediante `models.py`,
`triage_rules.py` y `sla_calculator.py`. Toda regla de negocio DEBE vivir allí: las
severidades P0–P3, los plazos P0 60 min y P1 240 min en 24/7, P2 480 min y P3 1440 min
en jornada hábil de lunes a viernes [08:00,18:00) sin festivos, y los `datetime` naive
de una única hora local. El escalamiento se activa al 75 % del plazo y persiste tras
el vencimiento; `resolved_at` detiene el reloj; el incumplimiento exige superar
estrictamente el plazo.

Los equipos válidos, los estados `OPEN`/`IN_PROGRESS`/`ESCALATION_REQUIRED`/`RESOLVED`
y la clave de duplicados `component:symptom_category` se definen una sola vez en el
dominio. El `incident_id` NO DEBE influir en la clasificación. El texto no reconocido
se devuelve como P3 provisional con revisión humana. `consistency_ratio` existe solo
por compatibilidad y NO DEBE presentarse como medida de confianza.

### II. Arquitectura Hexagonal estricta

La dependencia apunta siempre hacia el centro, conforme a ADR-003. `src/domain/` NO
DEBE importar `src.application`, `src.adapters`, frameworks HTTP, ORMs ni motores de
base de datos. `src/application/` DEBE contener `services.py` con los casos de uso
compartidos y `ports.py` con los puertos secundarios definidos con `typing.Protocol`,
en particular `IncidentRepositoryPort`. `src/adapters/inbound/` DEBE alojar REST y CLI;
un futuro adaptador MCP se añade allí sin duplicar lógica. `src/adapters/outbound/`
DEBE ser intercambiable mediante `DATABASE_URL`, resuelta en el borde y nunca en el
dominio. Cualquier cambio de puerto o de motor exige un ADR previo; la ampliación
actual de `IncidentRepositoryPort` está registrada en ADR-004.

### III. Paridad de adaptadores primarios

REST y CLI DEBEN invocar el mismo caso de uso de `IncidentService` —por ejemplo,
`triage_incident` o `get_active_incidents_summary`— y devolver el mismo resultado
observable y el mismo JSON para un mismo reporte. Los adaptadores NO DEBEN
reimplementar reglas de triaje ni normalizaciones propias: la normalización de
argumentos de negocio corresponde a la aplicación. Un cambio de contrato DEBE
reflejarse en ambos canales y cubrirse con escenarios BDD compartidos. Un futuro
adaptador MCP queda sujeto a la misma obligación de delegación.

### IV. Gobernanza tecnológica y dependencias

El proyecto DEBE usar Python >= 3.10 y gestionar entorno y dependencias con `uv`,
siendo `uv.lock` la fuente de verdad. El stack de entrega es FastAPI + Pydantic v2
para REST, Typer para CLI y `uvicorn` para servir. La persistencia DEBE emplear
`sqlite3` de la biblioteca estándar, sin ORMs pesados, según ADR-001, hasta que un
ADR específico autorice otro motor. `tiktoken` se reserva a la auditoría de contexto
y NO DEBE incorporarse al runtime.

### V. Verificación obligatoria

Ningún hito se da por cerrado sin sus comprobaciones. Las fronteras hexagonales se
verifican con `uv run ruff check src/`, usando TID251 `banned-api` y TID252
`ban-relative-imports = "parents"` con `select = ["E4", "E7", "E9", "F", "TID"]` y
archivos `ruff.toml` jerárquicos por capa. Los requisitos se especifican en BDD
`Given / When / Then`, se mapean 1:1 a funciones `test_bdd_*` y se ejecutan con
`uv run pytest -v`. Las violaciones de frontera NO DEBEN silenciarse con `noqa`.

## Fronteras y decisiones registradas

 Las decisiones estructurales se registran con la plantilla MADR en `docs/adr/`.
ADR-003 adopta la Arquitectura Hexagonal frente a capas acopladas a un único stack.
ADR-001 fija SQLite3 estándar sin ORM; ADR-002 rige el cálculo de SLA en horario
hábil; ADR-004 amplía `IncidentRepositoryPort` con operaciones de persistencia y
devolución de entidades de dominio. Un cambio de regla de dominio, de puerto o de
motor requiere ADR aceptado y la consiguiente actualización de esta constitución. La
precedencia ante conflicto es Constitución > ADR > especificación > `AGENTS.md`.

## Flujo de trabajo y calidad

 Cada hito se entrega con especificación BDD, evidencia de ejecuciones reales y
pruebas automatizadas. La documentación, los comentarios y las evidencias se
escriben en español. Los registros de ejecución ya producidos se preservan: NO DEBEN
reescribirse para ajustarlos al código. `AGENTS.md` es la guía operativa derivada y
no puede contradecir esta constitución.

## Governance

 Esta constitución prevalece sobre cualquier práctica o hábito local. Las enmiendas
requieren un ADR aceptado, una revisión de cumplimiento y el incremento de versión
según semántica: MAJOR para retirar o redefinir principios, MINOR para añadir
secciones o ampliar guía de forma material, PATCH para aclaraciones sin cambio
semántico. Toda revisión DEBE comprobar `uv run ruff check src/` y
`uv run pytest -v` antes de aprobar cambios en `src/`. La complejidad adicional DEBE
justificarse mediante ADR.

**Version**: 1.2.0 | **Ratified**: 2026-11-21 | **Last Amended**: 2026-11-21
