# Especificación — H002 Resumen de incidentes activos

Consultar el resumen de incidentes actualmente activos (`OPEN` e `IN_PROGRESS`) desde web y terminal, con total activo, número de incumplimientos de SLA y detalle por incidente, con filtro opcional por componente. H002 no registra ni modifica incidentes: solo lee el conjunto sembrado a través del adaptador de persistencia.

## Decisiones de alcance

- **Origen de datos**: el repositorio SQLite sembrado, obtenido por la fábrica del adaptador de salida. Es lectura de un conjunto ya sembrado, sin persistencia de nuevos registros ni escritura de estado.
- **Instante de referencia**: opcional. Si se envía, es una fecha ISO-naive (`YYYY-MM-DDTHH:MM:SS`) sin zona horaria; si no se envía, se usa el momento actual. Las fechas con zona horaria o con formato inválido se rechazan.
- **Activos**: solo estados `OPEN` e `IN_PROGRESS`. Se excluyen `ESCALATION_REQUIRED` y `RESOLVED`, tengan o no fecha de cierre.
- **Filtro**: `component` es opcional, de coincidencia exacta y sensible a mayúsculas. Ausente o vacío significa sin filtro.
- **Agregados**: `total_active` y `breached_count` se calculan sobre el conjunto resultante después del filtro. El detalle se ordena por identificador de incidente de forma ascendente.

## Contrato HTTP

- `GET /api/v1/incidents/active`
- Parámetros de consulta opcionales: `component` (cadena) y `reference_time` (ISO-naive).
- Éxito: `200 OK` con el objeto de respuesta descrito abajo.
- Parámetro inválido, inclusa una fecha con zona horaria: `422 Unprocessable Entity`.
- Fallo interno: `500`.

## Contrato CLI

- Subcomando: `active-incidents [--component <componente>] [--reference-time <ISO-naive>]`.
- Éxito: imprime en stdout el mismo objeto JSON que la respuesta HTTP y termina con código `0`.
- Entrada inválida: error y código `1`.

## Formato de respuesta

```json
{
  "total_active": 3,
  "breached_count": 2,
  "incidents": [
    {
      "incident_id": "INC-A",
      "title": "...",
      "component": "...",
      "severity": "P0",
      "status": "OPEN",
      "elapsed_minutes": 90,
      "requires_escalation": true
    }
  ]
}
```

`breached_count` cuenta los incidentes del conjunto filtrado cuyo plazo de SLA se ha superado estrictamente. `requires_escalation` sigue la regla del 75 % del dominio y permanece activo tras el vencimiento.

## Datos canónicos de aceptación

Cuatro incidentes sembrados con un instante de referencia fijo:

| Incidente | Componente | Severidad | Estado | Minutos transcurridos |
| --- | --- | --- | --- | --- |
| INC-A | payments-gateway | P0 | OPEN | 90 |
| INC-B | payments-gateway | P1 | IN_PROGRESS | 200 |
| INC-C | auth-identity | P1 | OPEN | 300 |
| INC-D | reporting-api | P3 | RESOLVED | 30 |

Con este conjunto: sin filtro hay tres activos y dos incumplimientos; filtrando por `payments-gateway` hay dos activos y un incumplimiento; filtrando por `frontend-ui` no hay activos.

## Escenarios BDD

### Escenario 1 — Resumen de incidentes activos

**Given** el conjunto canónico con tres incidentes activos y uno resuelto<br>
**When** se consulta el resumen en el instante de referencia acordado<br>
**Then** el total activo es 3, los incumplimientos son 2 y el detalle incluye, para cada activo, su identificador, título, componente, severidad, estado, minutos transcurridos y necesidad de escalamiento, ordenados por identificador.

### Escenario 2 — Filtro por componente

**Given** el conjunto canónico con activos en dos componentes distintos<br>
**When** se consulta el resumen filtrado por `payments-gateway`<br>
**Then** solo se detallan los incidentes de ese componente y los totales se recalculan sobre ellos: dos activos y un incumplimiento.

### Escenario 3 — Componente sin incidentes activos

**Given** el conjunto canónico, que no tiene activos en `frontend-ui`<br>
**When** se consulta el resumen filtrado por `frontend-ui`<br>
**Then** la consulta tiene éxito, el total activo y los incumplimientos son cero y el detalle está vacío.

### Escenario 4 — Paridad entre API y CLI

**Given** el mismo conjunto canónico y el mismo instante de referencia<br>
**When** se consulta el resumen por la API HTTP y por la CLI<br>
**Then** ambas devuelven el mismo objeto JSON, con los mismos totales y el mismo detalle.

### Escenario 5 — Instante de referencia inválido

**Given** una fecha de referencia con zona horaria explícita o con formato inválido<br>
**When** se envía la consulta por la API HTTP y por la CLI<br>
**Then** la API responde `422 Unprocessable Entity` y la CLI termina con error y código `1`.

## Fuera de alcance de H002

Registro de incidentes, ciclo de vida, detección de duplicados, paginación, orden configurable, festivos, conversión de zonas horarias, autenticación y CORS.
