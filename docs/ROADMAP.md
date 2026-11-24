# Roadmap — IncidentOps

Hitos planificados, en orden incremental. Cada cierre se documenta con evidencia de ejecución.

| Hito | Objetivo de producto y operación |
| --- | --- |
| H001 — Triaje multi-interfaz | Clasificación y enrutamiento determinista de reportes, sin persistencia, disponibles de inmediato desde web y terminal. |
| H002 — Resumen de incidentes activos | Consulta de incidentes activos e incumplimientos de SLA, con filtrado por componente, desde web y terminal. |
| H003 — Ciclo de vida, duplicados y SLA | Registro persistente de incidentes entrantes, aviso cuando ya exista otro equivalente abierto y auditoría del SLA en cualquier instante de referencia. |
| H004 — Persistencia relacional y contenedores | Ejecución reproducible en contenedores con base de datos relacional dedicada y comprobación real de conectividad operativa. |

Secuencia: H001–H002 cubren la consulta sin persistencia · H003 introduce el ciclo de vida · H004 cubre el entorno de ejecución y la operabilidad.
