# Feature Specification: Resumen de incidentes activos

**Feature Branch**: `003-active-incidents-summary`

**Created**: 2026-11-21

**Status**: Draft

**Input**: User description: "Necesitamos consultar el resumen de incidentes actualmente activos (OPEN e IN_PROGRESS) tanto por API HTTP como por CLI, indicando el total activo, cuántos incumplieron su SLA y el detalle de cada incidente (título, componente, severidad, estado, minutos transcurridos y si requiere escalamiento), permitiendo filtrar opcionalmente por componente."

## Clarifications

### Session 2026-11-21

- Q: ¿Qué interfaces expone el resumen y cómo se aplica el filtro? → A: `GET /api/v1/incidents/summary` con query parameter opcional `component`; subcomando CLI `summary [--component ...] [--reference-time ...]`.
- Q: ¿Qué resultado se devuelve cuando no hay incidentes activos o no hay coincidencias para el componente? → A: `200 OK` con JSON válido: `total_active=0`, `breached_count=0`, `incidents=[]`.
- Q: ¿Cómo se fija el instante de referencia para que las evaluaciones sean deterministas? → A: parámetro opcional `reference_time`; si se omite, se usa el instante actual.
- Q: ¿Qué cobertura BDD debe tener la aceptación? → A: exactamente 4 escenarios `Given/When/Then` en lenguaje de negocio: resumen global excluyendo `RESOLVED` y `ESCALATION_REQUIRED` —solo se consideran activos `OPEN` e `IN_PROGRESS`—, resumen filtrado por componente, caso vacío y consulta equivalente por CLI.

**Detalle técnico de adaptadores (acordado; no forma parte del lenguaje de negocio)**: el canal HTTP responde en `GET /api/v1/incidents/summary?component=<componente>&reference_time=<fecha ISO local sin zona>`, y el canal CLI expone `summary --component <componente> --reference-time <fecha ISO local sin zona>`. Ambos entregan la misma estructura JSON, con las claves `total_active`, `breached_count` e `incidents`; cada elemento del detalle incluye `incident_id`, `title`, `component`, `severity`, `status`, `elapsed_minutes` y `requires_escalation`. Esta nomenclatura sustituye la preliminar `/api/v1/incidents/active` y `active-incidents` del borrador `002`.

**Notas de integración**: un incidente ya escalado (`ESCALATION_REQUIRED`) deja de listarse aunque siga sin resolverse; su seguimiento queda fuera de este resumen. El rechazo de una fecha de referencia inválida o anterior a la creación de un incidente (FR-009, FR-013, SC-005) se comprueba con pruebas de adaptador, no con los 4 escenarios BDD acordados. La semántica completa de errores se define en `contracts/summary-api.md`. El medio de consulta es el servicio HTTP, no una interfaz de usuario; la terminal es el otro canal. Los valores numéricos canónicos se definen en `data-model.md > Dataset canónico de aceptación`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver el estado de los incidentes activos (Priority: P1)

El personal de soporte necesita una vista única de los incidentes que siguen abiertos o en atención para saber cuántos hay, cuántos han superado su plazo de atención y cuál es la situación de cada uno, sin revisar los registros uno por uno.

**Why this priority**: Responde a la necesidad central de la petición: tener en un solo lugar el total activo, los incumplimientos de SLA y el detalle de cada incidente. Sin esta historia no existe resumen que entregar.

**Independent Test**: Se verifica con un conjunto de cuatro incidentes de prueba —tres activos y uno resuelto— comprobando que el resumen muestra 3 activos, 2 incumplimientos y el detalle completo de los tres activos, sin incluir el resuelto.

**Acceptance Scenarios**:

1. **Given** un conjunto con tres incidentes abiertos o en atención y uno resuelto, **When** se consulta el resumen global en el instante de referencia acordado, **Then** el total activo es 3, los incumplimientos son 2 y el detalle enumera solo los tres incidentes activos con su identificador, título, componente, severidad, estado, minutos transcurridos y necesidad de escalamiento, excluyendo el resuelto.

---

### User Story 2 - Obtener el mismo resumen desde la terminal (Priority: P2)

El personal de operación que trabaja desde la terminal necesita acceder al mismo resumen, con los mismos filtros y los mismos resultados, para no depender del canal HTTP durante la atención de incidentes.

**Why this priority**: El requerimiento pide explícitamente ambos canales. Es la segunda prioridad porque el valor de negocio ya existe en el canal HTTP y la terminal extiende el acceso sin cambiar el significado de los datos.

**Independent Test**: Se verifica ejecutando una consulta por el canal HTTP y otra por la terminal sobre el mismo conjunto y el mismo instante de referencia, y comparando los resultados.

**Acceptance Scenarios**:

1. **Given** el mismo conjunto de incidentes y el mismo instante de referencia, **When** se consulta el resumen por el canal HTTP y por la terminal, **Then** ambos canales muestran el mismo total, el mismo número de incumplimientos y el mismo detalle, en el mismo orden y con la misma estructura.

---

### User Story 3 - Reducir el resumen a un componente (Priority: P3)

Quien atiende un componente concreto necesita acotar el resumen a ese componente para eliminar ruido y recalcular los totales solo sobre los incidentes de su responsabilidad.

**Why this priority**: Mejora la usabilidad sobre un resumen que ya funciona, pero no es requisito para obtener la información básica.

**Independent Test**: Se verifica filtrando el conjunto de aceptación por un componente presente y por otro ausente, comprobando el detalle y los totales en cada caso.

**Acceptance Scenarios**:

1. **Given** activos en dos componentes distintos, **When** se filtra el resumen por el componente de pagos, **Then** solo se detallan los dos incidentes de ese componente y los totales se recalculan sobre ellos: 2 activos y 1 incumplimiento.
2. **Given** que no hay incidentes activos, o que el filtro por componente no tiene coincidencias, **When** se consulta el resumen, **Then** la consulta tiene éxito, los totales son cero y el detalle está vacío, con la misma respuesta vacía en ambos casos.

### Edge Cases

- Un incidente exactamente en el plazo de su SLA **no** cuenta como incumplimiento: el plazo debe haberse superado estrictamente.
- Un incidente en estado `RESOLVED` o `ESCALATION_REQUIRED` queda fuera del resumen, tenga o no fecha de cierre.
- Si no hay incidentes activos o no hay coincidencias para el componente, la consulta sigue siendo válida: el total y los incumplimientos son cero y el detalle está vacío. La forma exacta de esa respuesta queda fijada en Clarifications.
- Un filtro ausente o compuesto solo por espacios equivale a no filtrar.
- Una fecha de referencia con zona horaria explícita o con formato inválido se rechaza; solo se admite una fecha local sin zona.
- El escalamiento permanece activo después del vencimiento del plazo.
- Los minutos transcurridos se calculan hasta el instante de referencia, no hasta el momento en que se ejecuta la consulta cuando se indicó uno.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El resumen DEBE incluir únicamente incidentes cuyo estado sea `OPEN` o `IN_PROGRESS`.
- **FR-002**: El resumen DEBE mostrar el total de incidentes activos resultantes.
- **FR-003**: El resumen DEBE mostrar cuántos incidentes activos han superado estrictamente su plazo de atención.
- **FR-004**: El detalle DEBE incluir, por cada incidente, identificador, título, componente, severidad, estado, minutos transcurridos hasta el instante de referencia y si requiere escalamiento.
- **FR-005**: El detalle DEBE ordenarse por identificador de incidente de forma ascendente.
- **FR-006**: El sistema DEBE aceptar un filtro opcional por componente, de coincidencia exacta y sensible a mayúsculas; ausente, vacío o compuesto solo por espacios significa sin filtro.
- **FR-007**: Los totales DEBEN calcularse sobre el conjunto resultante después de aplicar el filtro.
- **FR-008**: El sistema DEBE aceptar un instante de referencia opcional en formato de fecha local sin zona horaria; si no se indica, DEBE usar el momento actual.
- **FR-009**: El sistema DEBE rechazar instantes de referencia con zona horaria explícita o formato inválido, sin devolver un resumen parcial.
- **FR-010**: El canal HTTP y la terminal DEBEN ofrecer el mismo resumen y la misma semántica de filtros y de errores.
- **FR-011**: La consulta NO DEBE registrar incidentes ni modificar su estado.
- **FR-012**: La ausencia de incidentes activos o de coincidencias con el filtro DEBE tratarse como un resultado válido, con totales a cero y detalle vacío, no como un error.
- **FR-013**: El sistema DEBE rechazar un instante de referencia anterior a la fecha de creación de cualquiera de los incidentes evaluados, sin devolver un resumen parcial.

### Key Entities *(include if feature involves data)*

- **Incidente activo**: registro con identificador, título, componente, severidad, estado, fecha de creación y, cuando aplica, fecha de cierre. Es la unidad que se lista en el detalle.
- **Resumen de activos**: agregado formado por el total de activos, el número de incumplimientos de SLA y la lista de incidentes activos con su información de atención.
- **Filtro por componente**: valor opcional que acota el resumen a un componente concreto y determina el conjunto sobre el que se calculan los totales.
- **Instante de referencia**: fecha local opcional que fija el momento desde el que se miden el tiempo transcurrido, el incumplimiento y el escalamiento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En el conjunto de aceptación de cuatro incidentes —tres activos y uno resuelto—, el resumen global excluye siempre el resuelto e identifica correctamente los 3 activos y los 2 incumplimientos, con un 100 % de acierto.
- **SC-002**: En el conjunto de aceptación, el filtro por el componente de pagos devuelve exactamente 2 activos y 1 incumplimiento, y un filtro sin coincidencias devuelve 0 activos y 0 incumplimientos.
- **SC-003**: El 100 % de los incidentes devueltos al filtrar pertenecen al componente solicitado.
- **SC-004**: El canal HTTP y la terminal producen resultados idénticos en el 100 % de las consultas de aceptación, incluidos los casos de filtro y de error.
- **SC-005**: El 100 % de las consultas con una fecha de referencia inválida, con zona horaria explícita o anterior a la creación de un incidente evaluado se rechazan sin mostrar un resumen parcial.
- **SC-006**: Una sola petición del usuario entrega el resumen completo incluso cuando existan hasta 10.000 incidentes registrados, sin requerir operaciones manuales adicionales.

## Assumptions

- Los incidentes ya están registrados en el sistema; esta funcionalidad solo los consulta y no modifica su ciclo de vida.
- Se consideran activos únicamente los estados `OPEN` e `IN_PROGRESS`.
- El instante de referencia es una fecha local sin zona horaria; por defecto se usa la fecha y hora actuales.
- El filtro por componente es exacto y sensible a mayúsculas; un valor vacío o compuesto solo por espacios equivale a no filtrar.
- Los totales se calculan después del filtro y el detalle se ordena por identificador ascendente.
- Los dos canales solicitados son el servicio HTTP y la terminal; no se asume ningún marco de trabajo, lenguaje ni motor de persistencia particular.
- Quedan fuera de alcance: registro de incidentes, ciclo de vida, detección de duplicados, paginación, orden configurable, festivos, conversión de zonas horarias, autenticación y CORS.
- No se crea ninguna rama git en este paso: no hay hook `before_specify` registrado en `.specify/extensions.yml`.
- Existe un borrador manual previo en `specs/002-active-incidents-summary.md`; esta especificación pasa a ser la fuente formal para las fases posteriores.
