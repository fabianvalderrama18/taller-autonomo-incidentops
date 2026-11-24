# ADR-005: Contrato de duplicados y tiempo del ciclo de vida
- **Estado**: Aceptado
- **Fecha**: 2026-11-24
- **Autor(es)**: Equipo IncidentOps
- **Reemplaza a**: Parcialmente ADR-004 (puerto de búsqueda de duplicados) y ADR-002 (entrada temporal de H003).

## 1. Contexto y Problema
El ciclo de vida requiere equivalencia semántica, no coincidencia de componente y severidad. Los clientes pueden emitir instantes con desplazamiento UTC. La decisión es establecer el contrato de identidad y tiempo del ciclo de vida compartido.

## 2. Opciones Consideradas
1. **Conservar coincidencia por componente/severidad y rechazar zonas**: mantiene compatibilidad, pero confunde síntomas distintos y rechaza instantes inequívocos.
2. **Clave de triaje y hora de negocio normalizada**: preserva equivalencia entre canales y acepta offsets; exige migrar el puerto y declarar una zona de negocio.

## 3. Decisión Arquitectónica
Adoptar la segunda opción. Duplicados se buscan exclusivamente por clave, estados OPEN/IN_PROGRESS/ESCALATION_REQUIRED y exclusión del propio ID. El puerto deja de buscar por componente/severidad. H003 convierte instantes aware a America/Bogota y los almacena naive; naive significa hora de Bogotá. El dominio ofrece la normalización pura y mantiene el evaluador histórico estricto. H002 conserva su contrato de entrada. ID existente se rechaza (409), no se sobrescribe por la operación de creación.

## 4. Consecuencias y Trade-offs
- **Positivas**: equivalencia precisa y tiempo reproducible sin duplicar reglas.
- **Negativas / Trade-offs**: cambia el contrato del puerto; Bogotá pasa a ser una política explícita. La alerta de duplicados describe los registros visibles al consultar; no garantiza deduplicación transaccional bajo altas simultáneas.
