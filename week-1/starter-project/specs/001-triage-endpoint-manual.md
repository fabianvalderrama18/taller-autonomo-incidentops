# Especificación manual — H001 Triaje multi-interfaz

Contrato acordado: HTTP `POST /api/v1/incidents/triage` con `{"incident_id": str, "raw_text": str}`; `200 OK` devuelve todos los campos de `TriageResult`; campos vacíos o solo espacios tras `.strip()` devuelven `422`. La CLI `triage --incident-id ... --raw-text ...` imprime el mismo JSON en stdout, con código `0` al clasificar y `1` ante entradas vacías. Ambos canales invocan `IncidentService.triage_incident` sin persistencia.

## Escenarios BDD

### Escenario 1 — Caída crítica HTTP 502 en pasarela de pagos

**Given** un reporte de indisponibilidad generalizada de pagos con HTTP 502<br>
**When** se envía mediante `POST /api/v1/incidents/triage`<br>
**Then** la respuesta es `200` con `severity="P0"`, `component="payments-gateway"`, `recommended_team="Backend-Core"` y `duplicate_group_key="payments-gateway:payment_http_502"`.

### Escenario 2 — Cuenta individual bloqueada mencionando "hoy"

**Given** un reporte de bloqueo de cuenta individual que incluye la palabra "hoy"<br>
**When** se clasifica mediante el endpoint HTTP<br>
**Then** la respuesta es `200` con `severity="P2"` y `recommended_team="Security-IAM"`, sin falso positivo P0.

### Escenario 3 — Entradas vacías o con solo espacios

**Given** `raw_text=" "` o `incident_id=""`<br>
**When** se envía la petición al endpoint HTTP<br>
**Then** se devuelve `422 Unprocessable Entity` y no se clasifica el reporte.

### Escenario 4 — Paridad en CLI

**Given** el reporte canónico `INC-1001`<br>
**When** se ejecuta `triage --incident-id INC-1001 --raw-text "..."`<br>
**Then** la CLI imprime JSON válido en stdout con `severity="P0"` y `recommended_team="Backend-Core"`, y termina con código de salida `0`.

### Escenario 5 — Entradas vacías en la CLI

**Given** `raw_text="   "` o `incident_id=""`<br>
**When** se ejecuta el subcomando `triage` con ese valor<br>
**Then** la CLI termina con error y código de salida `1`.

## Nota de consistencia

Resuelto: el Escenario 1 usa `payments-gateway:payment_http_502`, la clave canónica que produce el dominio (ver `src/domain/triage_rules.py`). No se modificaron las reglas de triaje para automatizar la prueba.
