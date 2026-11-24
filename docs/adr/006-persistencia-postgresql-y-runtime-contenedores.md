# ADR-006: Persistencia dual con servidor PostgreSQL
- **Estado**: Aceptado
- **Fecha**: 2026-11-24
- **Autor(es)**: Equipo IncidentOps
- **Reemplaza a**: Parcialmente ADR-001, restricción de solo sqlite3 sin dependencias externas.

## 1. Contexto y Problema
El servicio necesita almacenamiento relacional dedicado y ejecución reproducible. Se conserva SQLite para desarrollo. Este es el ADR-004 solicitado por el taller; se numera 006 porque 004 ya registra el puerto y 005 registra el contrato de ciclo de vida.

## 2. Opciones Consideradas
1. **SQLite sobre volumen del contenedor de API**: operación sencilla y sin red; limita concurrencia de escritura y acopla almacenamiento al proceso de aplicación.
2. **PostgreSQL dedicado con SQLite local**: servidor transaccional independiente y varios clientes; requiere un driver, supervisión y pruebas de paridad entre motores.

## 3. Decisión Arquitectónica
Adoptar persistencia dual sin ORM con psycopg[binary], seleccionada por DATABASE_URL. La topología Docker Compose separa api y db (postgres:16-alpine), con volumen persistente y salud de ambos servicios. Los instantes se almacenan como TEXT ISO 8601 normalizado, preservando semántica temporal entre motores. La salud ejecuta SELECT 1 real y falla si no hay conectividad.

## 4. Consecuencias y Trade-offs
- **Positivas**: el núcleo no depende del motor; despliegue reproducible y datos fuera del contenedor efímero de API.
- **Negativas / Trade-offs**: dos dialectos SQL y mantenimiento de índices; TEXT no impone tipos temporales en el motor. El orden de arranque no evita fallos de conectividad posteriores, por lo que la salud se evalúa en cada solicitud.
