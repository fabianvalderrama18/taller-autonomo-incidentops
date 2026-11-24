# Plan 004-postgres-container-runtime

Constitución 2.0.0; ADR-003/005/006.

Implementar adaptador psycopg con dict_row, parámetros %s y upsert, mismo puerto y esquema lógico que SQLite. Factory selecciona motor; servicio consulta salud y traduce fallos sin filtrar secretos. Contenedores con dependencia por salud y lock reproducible. Pruebas locales sin daemon y paridad real si PostgreSQL está disponible.
