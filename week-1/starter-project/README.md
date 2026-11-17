IncidentOps — Entrega del taller Semana 1

Autor: Alvaro

Contenido

src/models.py y src/triage_rules.py: triaje determinista con equipo y agrupación de duplicados.
src/sla_calculator.py: SLA 24/7 o en horario hábil y escalamiento desde el 75%.
docs/adr/002-calculo-sla-horario-habil.md: decisión y diagrama Mermaid.
CONTEXT_LOG.md: bitácora, decisiones, comparación de modelos, mediciones y estado metodológico.
tests/: pruebas adicionales con biblioteca estándar.
evidencias/: salidas reales, respuestas de los modelos y copias del código original.

Ejecución desde week-1/starter-project

uv sync
uv run python -m src.triage_rules
uv run python -m src.sla_calculator
uv run python -m unittest discover -s tests -v
uv run python -m src.context_audit --symbol classify_incident_report
uv run python -m src.context_audit --symbol evaluate_sla_status
uv run python -m src.context_audit --compare-formats

Verificación de integración opcional

uv run python -m src.incident_repository --records 10000 --iterations 1

Este último comando conserva el repositorio original y sus consultas N+1. La refactorización SQL no forma parte de los dos retos entregables del PDF.

Contrato temporal

Los datos utilizan datetime sin zona y una única hora local de negocio. P2/P3 cuentan lunes a viernes de 08:00 a 18:00, sin calendario de festivos. Los umbrales utilizan segundos exactos y los campos de minutos se truncan al final. El estado resuelto o una fecha de resolución impiden solicitar escalamiento.

Estado

Los dos retos y el ADR están completos y verificados. La propuesta del chat limpio quedó preservada en evidencias/chat-limpio-sla, y sus mejoras se integraron en el cálculo definitivo. La suite contiene 20 métodos de prueba, además de las demostraciones ejecutables de triaje y SLA. CONTEXT_LOG.md documenta la secuencia real, las decisiones y las mediciones finales.

La comparación de modelos cambia tanto modelo como esfuerzo de razonamiento; no se presenta como experimento que aísle una única variable. Las mediciones de tokens corresponden a los payloads del script, que simula LSP mediante AST.
