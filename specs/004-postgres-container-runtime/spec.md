# Persistencia dual y runtime

Estado: contrato definido antes de implementación.

## Contrato y clarificaciones
GET /health y CLI health ejecutan SELECT 1: 200 y {"status":"ok","database":"connected"}; fallo 503 y {"status":"error","database":"unavailable"}, CLI 1. PostgreSQL por postgresql://; SQLite por sqlite:/// o ausencia (:memory:). URL desconocida se rechaza. RNF: connect_timeout=3 segundos, SQL parametrizado, sin ORM, conexiones cerradas por operación; memoria SQLite compartida durante vida de la app. Python 3.12-slim, uv frozen, db postgres:16-alpine, volumen, pg_isready, depends_on service_healthy y healthcheck HTTP.

## Escenarios BDD

### salud_operativa
**Given** el almacenamiento responde.
**When** se consulta la salud por web y terminal.
**Then** se informa conectividad disponible.

### salud_no_disponible
**Given** el almacenamiento no responde.
**When** se consulta la salud.
**Then** se informa indisponibilidad sin exponer credenciales.

### seleccion_de_motor
**Given** hay configuración SQLite o PostgreSQL.
**When** se obtiene persistencia.
**Then** ambos motores ofrecen el mismo contrato.

### runtime_reproducible
**Given** se dispone del proyecto y Docker Compose.
**When** se valida la topología.
**Then** api y db tienen chequeos de salud y almacenamiento persistente.
