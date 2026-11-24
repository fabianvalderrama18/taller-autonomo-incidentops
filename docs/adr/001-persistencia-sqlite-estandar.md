# ADR-001: Persistencia con SQLite3 estándar y sin ORM

- **Estado**: Aceptado
- **Fecha**: 2026-11-21
- **Autor(es)**: Alvaro
- **Reemplaza a**: Ninguno

---

## 1. Contexto y Problema

El roadmap incorpora persistencia del ciclo de vida, resumen de incidentes activos y ejecución en contenedores. El repositorio actual ya resuelve la consulta con `sqlite3` de la biblioteca estándar, pero todavía no hay una decisión registrada que fije el motor y el nivel de abstracción. Sin esa decisión, cada adaptador podría introducir su propio ORM o su propia forma de construir la conexión, y la elección terminaría filtrándose al núcleo de reglas. Las restricciones vigentes son: conservar el comportamiento verificado, mantener el dominio libre de infraestructura, no añadir dependencias de runtime innecesarias y permitir cambiar de motor más adelante mediante un ADR específico.

---

## 2. Opciones Consideradas

1. **Opción A — ORM completo (por ejemplo, SQLAlchemy)**:
   - *Ventajas*: mapeo automático de entidades, migraciones y abstracción de SQL; reduce código repetitivo en operaciones complejas.
   - *Desventajas*: añade una dependencia pesada al runtime, acopla el modelo de dominio al esquema de la biblioteca y desplaza la complejidad hacia la configuración; resulta desproporcionado para un taller con un único motor y consultas simples.
2. **Opción B — SQLite3 del estándar sin ORM**:
   - *Ventajas*: cero dependencias nuevas, control explícito del SQL y del esquema, compatibilidad con el código y las evidencias ya verificadas, y sustitución del adaptador sin tocar el dominio.
   - *Desventajas*: SQL y gestión de conexiones manuales; cualquier cambio de motor exige reescribir el adaptador, y las consultas ineficientes deben detectarse y corregirse deliberadamente.

---

## 3. Decisión Arquitectónica

Elegimos la Opción B. La persistencia se implementa en `src/adapters/outbound/` con `sqlite3` de la biblioteca estándar, sin ORM. La conexión se crea en el borde: el constructor de `IncidentRepository` acepta hoy una ruta o `:memory:`, y la configuración mediante `DATABASE_URL` se resolverá en ese mismo adaptador cuando la persistencia entre en el caso de uso (H003/H004). En H001 la operación de triaje es stateless y no invoca la base de datos.

El dominio no conoce el motor: `src/domain/` importa únicamente entidades y reglas propias. El repositorio implementará el puerto secundario declarado en `src/application/ports.py`, de modo que sustituir SQLite por otro motor sea un cambio de adaptador. Cualquier cambio de motor requiere un ADR previo que reemplace o complemente esta decisión.

El escaneo completo de tabla y las consultas N+1 de `get_active_incidents_summary` se conservan como artefacto pedagógico del benchmark; no se corrigen en este ADR ni en H001.

---

## 4. Consecuencias y Trade-offs

- **Positivas**: dependencias de runtime reducidas, coherencia con el código y las evidencias existentes, frontera de persistencia explícita y posibilidad de cambiar de adaptador sin alterar reglas de triaje ni de SLA.
- **Negativas / Trade-offs**: responsabilidad manual sobre SQL, esquema y conexiones; portabilidad limitada a motores que puedan implementar el puerto; el cambio de motor tendrá un costo real de reescritura del adaptador, asumido conscientemente.
