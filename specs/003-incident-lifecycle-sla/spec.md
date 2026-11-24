# Ciclo de vida, duplicados y SLA

Estado: contrato definido antes de implementación.

## Contrato y clarificaciones
POST /api/v1/incidents: title y raw_text no vacíos; incident_id opcional INC-<HEX8>, created_at opcional ahora Bogotá, status OPEN por defecto (cuatro estados válidos). 201 con clasificación completa, campos de incidente, is_duplicate y duplicate_of ordenado. ID repetido: 409; entrada inválida: 422. GET /api/v1/incidents/{id}/sla: 200, 404 o 422. CLI create/sla: JSON y 0; error por stderr y 1. Fechas ISO con hora; offsets normalizados a Bogotá. RESOLVED sin resolved_at no congela un instante desconocido: se evalúa hasta la referencia y se suprime escalamiento. No se ofrece transición de estado en este hito.

## Escenarios BDD

### registro_inicial
**Given** no hay incidentes equivalentes.
**When** se registra un reporte válido.
**Then** se conserva la clasificación completa sin duplicados.

### duplicado_abierto
**Given** hay equivalentes abiertos y resueltos.
**When** se registra otro reporte equivalente.
**Then** se enumeran solo los abiertos excluyendo el propio identificador.

### sla_habil
**Given** un P2 se creó el viernes 2026-11-06 a las 17:00.
**When** se audita el lunes 2026-11-09 a las 09:00.
**Then** transcurrieron 120 de 480 minutos, quedan 360 y no hay vencimiento ni escalamiento.

### errores_de_auditoria
**Given** un identificador no existe o el instante precede la creación.
**When** se solicita la auditoría.
**Then** se informa ausencia o entrada inválida sin cambiar datos.

### paridad_cli
**Given** el mismo reporte y referencia están disponibles.
**When** se registra y audita por web y terminal.
**Then** los resultados son equivalentes.
