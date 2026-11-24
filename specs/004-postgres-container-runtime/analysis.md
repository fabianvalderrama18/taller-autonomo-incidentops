# Auditoría previa

Sin reglas de triaje/SLA en adaptadores. Cada escenario tiene una función test_bdd homónima. La búsqueda heredada por severidad no satisface H003 y cambia mediante ADR-005. Los timestamps se normalizan antes de guardar. Salud debe capturar también fallos al conectar, no solamente SELECT 1. ADR-006 autoriza psycopg antes de H004. No se atribuye esta revisión a comandos OpenCode que no se ejecutaron.
