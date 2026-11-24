---
name: adr-writer
description: Redacta decisiones arquitectónicas de IncidentOps en MADR estricto cuando cambian fronteras, persistencia o topología. No sustituye especificaciones BDD ni planes de implementación.
---

# Registro de decisiones

Lee la Constitución vigente, los ADR previos y `docs/adr/000-template.md`.
Usa esa plantilla: Estado, Fecha, Autor(es), Reemplaza a y, cuando corresponda,
Reemplazado por. Registra exactamente una decisión estructural difícil de revertir.
Compara al menos dos opciones reales con ventajas y costes auténticos.
Conserva los registros aceptados: cambios mediante un ADR nuevo (append-only).
Explicita reemplazos parciales sin borrar antecedentes. Si un número está ocupado,
usa el siguiente libre y documenta la correspondencia con el enunciado.
Mermaid es opcional y únicamente estructural: capas, límites o topología;
no dibujes flujos if/else. No añadas Componentes Afectados, enlaces frágiles,
comandos de verificación, criterios BDD ni listas de archivos/tareas del plan.
Tras registrar la decisión, actualiza la Constitución antes de especificar el hito.
