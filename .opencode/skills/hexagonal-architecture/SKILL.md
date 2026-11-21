---
name: hexagonal-architecture
description: Aplica y verifica la Arquitectura Hexagonal de IncidentOps (ADR-003): reglas de importación por capa, paridad obligatoria entre adaptadores primarios y control estático de fronteras con Ruff. Úsala al tocar src/, añadir adaptadores, definir puertos o cambiar dependencias.
---

# Arquitectura Hexagonal — IncidentOps

Principio rector (ADR-003 y Constitución, artículos I–II): las dependencias apuntan siempre hacia el centro. El dominio es la única fuente de verdad de triaje y SLA; las capas externas solo traducen y delegan.

## 1. Reglas de importación por capa

### `src/domain/`
- **Puede importar**: biblioteca estándar (`dataclasses`, `datetime`, `typing`, `unicodedata`, `pathlib`, `json`, `re`, …) y otros módulos de `src.domain`.
- **No puede importar**: ningún framework ni módulo de HTTP (FastAPI, Pydantic, Typer, Starlette), ningún driver de base de datos ni ORM (`sqlite3`, SQLAlchemy, …), `src.application`, `src.adapters` ni cualquier capa externa.
- Contiene solo entidades y reglas puras y deterministas (`models.py`, `triage_rules.py`, `sla_calculator.py`). No hace I/O de infraestructura ni reimplementa reglas en los bordes.

### `src/application/`
- **Puede importar**: biblioteca estándar, `src.domain` y sus propios módulos.
- **No puede importar**: frameworks de entrega, drivers de BD, ORMs ni `src.adapters`.
- `services.py` expone los casos de uso compartidos (`IncidentService.triage_incident`). `ports.py` declara los puertos secundarios con `typing.Protocol`, en particular `IncidentRepositoryPort`.

### `src/adapters/inbound/`
- **Puede importar**: FastAPI, Pydantic y Typer según el canal; `src.application`, `src.domain` y `src.adapters.outbound.factory` para obtener un repositorio cuando el caso de uso lo necesite.
- **No puede importar**: drivers de base de datos (`sqlite3`) ni repositorios concretos (`src.adapters.outbound.incident_repository`) directamente. Para persistencia, usa siempre `src.adapters.outbound.factory`.
- **Obligación**: delegar siempre en `IncidentService`. REST y CLI no contienen reglas de triaje, normalizaciones propias ni cálculos de SLA.

### `src/adapters/outbound/`
- **Puede importar**: `sqlite3` y la configuración de entorno (`DATABASE_URL`), `src.domain` para las entidades y `src.application.ports` para implementar `IncidentRepositoryPort`.
- **No puede importar**: adaptadores primarios, FastAPI, Pydantic ni Typer.
- Expone `src/adapters/outbound/factory.py` como único punto de construcción del repositorio; el motor se sustituye cambiando el adaptador, nunca el dominio.

## 2. Paridad de adaptadores primarios

REST (`src/adapters/inbound/api/`) y CLI (`src/adapters/inbound/cli.py`) **deben invocar el mismo caso de uso** `IncidentService.triage_incident`. Un mismo reporte produce el mismo resultado y el mismo JSON en ambos canales; cualquier cambio de contrato se refleja en los dos y se cubre con los escenarios BDD compartidos de `tests/test_spec_001_triage.py`. Un futuro adaptador MCP se añade en `src/adapters/inbound/` con la misma delegación y sin duplicar lógica.

## 3. Verificación estática de fronteras

- En `pyproject.toml`, configurar `select = ["E4", "E7", "E9", "F", "TID"]` y, dentro de `flake8-tidy-imports`, `TID251 banned-api` junto con `TID252` mediante `ban-relative-imports = "parents"`.
- Mantener archivos jerárquicos `ruff.toml` en `src/domain/`, `src/application/` y `src/adapters/inbound/`, cada uno con la lista de módulos prohibidos correspondiente a su capa.
- Ejecutar siempre `uv run ruff check src/` antes de dar por cerrado un cambio. Cualquier import prohibido hace fallar la comprobación.
- No silenciar violaciones con `# noqa`: si una dependencia atraviesa una frontera, se decide y se registra mediante ADR, no se evita el check.

## Checklist rápido

1. ¿El nuevo código está en la capa correcta?
2. ¿Sus imports respetan la lista de permitidos de esa capa?
3. ¿Los adaptadores primarios delegan en `IncidentService` y no importan BD?
4. ¿REST y CLI devuelven exactamente el mismo resultado?
5. ¿Pasa `uv run ruff check src/`?
