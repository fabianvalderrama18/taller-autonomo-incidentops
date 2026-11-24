## 1. Diagnóstico del motor de triaje

La auditoría evidencia dos problemas principales: sobreclasificación de incidentes individuales por expresiones de urgencia y subclasificación de incidentes que podrían comprometer la confidencialidad de datos entre organizaciones.

El criterio propuesto es asignar severidad a partir del impacto comprobado o razonablemente sustentado, el alcance, la seguridad y la disponibilidad del servicio. Palabras como «urgente», «hoy» o «inmediatamente» no constituyen evidencia suficiente para asignar P0.

La clasificación siguiente es preliminar porque los reportes están truncados. Se diferencia entre hechos visibles, hipótesis y condiciones pendientes de validación.

## 2. Criterios de severidad

| Severidad | Criterio de asignación                                                                                                                                         | SLA vigente                 |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| P0        | Interrupción crítica generalizada de un servicio esencial, o compromiso grave de seguridad confirmado, con impacto amplio y necesidad de contención inmediata. | 60 minutos, 24x7            |
| P1        | Degradación severa de un servicio crítico, afectación importante de clientes o exposición sensible confirmada de alcance limitado.                             | 240 minutos, 24x7           |
| P2        | Fallo funcional o degradación moderada, con servicio principal disponible y sin evidencia de compromiso crítico de seguridad.                                  | 480 minutos, horario hábil  |
| P3        | Solicitudes cosméticas, mejoras menores o riesgos preventivos sin afectación actual en producción.                                                             | 1440 minutos, horario hábil |

La severidad debe reevaluarse cuando aparezcan nuevas evidencias. Un incidente de seguridad puede alcanzar P0 aunque el servicio continúe disponible.

## 3. Criterios de componente y equipo

El componente debe identificar el subsistema donde se manifiesta el problema, sin confundirlo necesariamente con la causa raíz.

| Componente         | Equipo recomendado | Responsabilidad                                              |
| ------------------ | ------------------ | ------------------------------------------------------------ |
| payments-gateway   | Backend-Core       | Procesamiento de pagos e integración de pasarelas            |
| auth-identity      | Security-IAM       | Autenticación, identidad y control de acceso                 |
| reporting-api      | Backend-Core       | Consultas, exportaciones y autorización de acceso a reportes |
| frontend-ui        | Backend-Core       | Interfaz y comportamiento funcional                          |
| database-cluster   | Data-DBA           | Bases de datos, replicación y rendimiento                    |
| infra-certificates | Platform-SRE       | Certificados, infraestructura y configuración TLS            |

La asignación de reporting-api a Backend-Core es la regla general. Cuando el síntoma corresponde a exposición de información entre organizaciones, Security-IAM debe asumir la investigación de seguridad, con Backend-Core como equipo colaborador.

## 4. Clasificación propuesta de los 10 incidentes

| ID       | Severity | Component          | Recommended_team | Duplicate_group_key                         |
| -------- | -------- | ------------------ | ---------------- | ------------------------------------------- |
| INC-1001 | P0\*     | payments-gateway   | Backend-Core     | `payments-gateway:payment_unavailable`      |
| INC-1002 | P2       | auth-identity      | Security-IAM     | `auth-identity:login_failure`               |
| INC-1003 | P2       | reporting-api      | Backend-Core     | `reporting-api:slow_query`                  |
| INC-1004 | P3       | frontend-ui        | Backend-Core     | `frontend-ui:cosmetic_request`              |
| INC-1005 | P1\*     | database-cluster   | Data-DBA         | `database-cluster:resource_saturation`      |
| INC-1006 | P0\*     | payments-gateway   | Backend-Core     | `payments-gateway:payment_unavailable`      |
| INC-1007 | P1\*     | reporting-api      | Security-IAM     | `reporting-api:cross_tenant_data_exposure`  |
| INC-1008 | P2       | reporting-api      | Backend-Core     | `reporting-api:slow_query`                  |
| INC-1009 | P2       | reporting-api      | Backend-Core     | `reporting-api:export_timeout`              |
| INC-1010 | P3       | infra-certificates | Platform-SRE     | `infra-certificates:certificate_expiration` |

Las clasificaciones marcadas con asterisco dependen de confirmar el impacto o la exposición descritos. No representan hechos plenamente verificados a partir de los extractos disponibles.

### Justificaciones verificables

| Incidente | Justificación y condición de validación                                                                                                                                                                                        |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| INC-1001  | El gateway devuelve HTTP 50x, indicio de fallo del procesamiento. P0 si afecta de forma generalizada los pagos en producción; en caso contrario, revisar P1 o P2.                                                              |
| INC-1002  | Se reportan tres intentos fallidos de acceso de un usuario. No existe evidencia visible de indisponibilidad general ni de ataque. P2 provisional.                                                                              |
| INC-1003  | El dashboard histórico presenta lentitud. No se evidencia caída total. P2 por degradación de rendimiento.                                                                                                                      |
| INC-1004  | Solicitud de modificación de color. No existe afectación funcional. P3.                                                                                                                                                        |
| INC-1005  | Se informa alto consumo de recursos del nodo primario PostgreSQL. P1 condicionado a degradación importante o riesgo inmediato de indisponibilidad; si solo es una alerta preventiva, P2.                                       |
| INC-1006  | Se reporta nuevamente una caída de la pasarela de cobros. P0 condicionado a indisponibilidad amplia del procesamiento de pagos.                                                                                                |
| INC-1007  | El extracto indica manipulación del parámetro `company`, pero no muestra el resultado. Si permite consultar facturas de otra organización, constituye una vulneración de aislamiento entre tenants y justifica P1 como mínimo. |
| INC-1008  | Lentitud del listado de planes e historial. P2 por degradación funcional, sin evidencia de indisponibilidad completa.                                                                                                          |
| INC-1009  | La exportación mensual a Excel queda bloqueada o tarda excesivamente. No hay evidencia de caída general ni de pérdida de datos. P2.                                                                                            |
| INC-1010  | Certificado TLS de staging próximo a vencer. Riesgo preventivo fuera de producción. P3.                                                                                                                                        |

## 5. Revisión especial

### INC-1002: autenticación individual

Se recomienda P2, no P0.

Hecho visible: un usuario informa que intentó ingresar tres veces.

No está demostrado que el sistema completo de autenticación esté indisponible. Tampoco se sabe si existe bloqueo de cuenta, error de credenciales, fallo de MFA o problema del proveedor de identidad.

Información necesaria: cantidad de usuarios afectados, códigos de error, registros de autenticación, estado del proveedor de identidad y existencia de bloqueos masivos.

Se elevaría a P1 o P0 si se confirma una interrupción significativa o generalizada de autenticación en producción.

### INC-1007: posible exposición entre organizaciones

Se recomienda P1 provisional, con investigación de seguridad prioritaria.

Hecho visible: el reporte menciona el cambio del parámetro `company`.

El contexto de la auditoría señala una posible exposición de facturas entre organizaciones, pero el extracto no permite confirmar qué información fue devuelta ni quién pudo acceder.

Si se verifica que cambiar ese parámetro permite recuperar facturas de otra organización sin autorización, el incidente corresponde a un fallo de autorización entre tenants, potencialmente un IDOR o BOLA.

Debe evaluarse P0 cuando se confirme una exposición grave y extendida, explotación activa o ausencia generalizada de controles de aislamiento.

Información necesaria: respuesta HTTP, identidad y permisos del solicitante, organizaciones involucradas, sensibilidad de las facturas, registros de acceso y alcance de la explotación.

La prioridad inmediata es validar la exposición y, de confirmarse, contenerla sin esperar a conocer la causa raíz.

### INC-1009: exportación mensual a Excel

Se recomienda P2, no P0.

Hecho visible: una exportación mensual queda procesando sin finalizar.

La criticidad no puede inferirse únicamente de la fecha límite de entrega ni de palabras como «hoy».

Información necesaria: porcentaje de exportaciones fallidas, usuarios afectados, duración de la operación, existencia de métodos alternativos y dependencia de procesos financieros obligatorios.

Podría elevarse a P1 si se demuestra que bloquea un proceso empresarial crítico sin alternativa operativa. P0 requeriría evidencia adicional de impacto excepcional.

## 6. Agrupación de duplicados

### INC-1001 e INC-1006

Clave compartida: `payments-gateway:payment_unavailable`

Ambos describen síntomas de indisponibilidad del procesamiento de pagos. Se recomienda agruparlos como candidatos a duplicado para facilitar correlación y análisis.

No debe concluirse automáticamente que tienen la misma causa raíz: podrían involucrar proveedores distintos, errores diferentes o ventanas temporales independientes.

### INC-1003 e INC-1008

Clave compartida: `reporting-api:slow_query`

Ambos describen lentitud en operaciones de consulta de reporting.

La agrupación permite identificar un posible problema transversal de rendimiento, pero requiere comprobar métricas de latencia, endpoints, consultas SQL y coincidencia temporal.

La clave `component:symptom_category` debe interpretarse como grupo de correlación, no como prueba definitiva de duplicidad.

## 7. Decisiones ambiguas pendientes

| Incidentes | Ambigüedad                                              | Evidencia requerida                                          |
| ---------- | ------------------------------------------------------- | ------------------------------------------------------------ |
| 1001, 1006 | P0 frente a P1                                          | Tasa de errores, transacciones afectadas, alcance y duración |
| 1002       | Fallo individual frente a incidente masivo              | Logs de autenticación y cantidad de cuentas afectadas        |
| 1005       | Saturación crítica frente a alerta preventiva           | CPU, memoria, conexiones, latencia y estado de replicación   |
| 1007       | Vulnerabilidad potencial frente a exposición confirmada | Prueba de acceso no autorizado, alcance y registros          |
| 1009       | Lentitud ordinaria frente a bloqueo empresarial crítico | Dependencias operativas y alternativas disponibles           |
| 1010       | Riesgo en staging frente a impacto productivo           | Entorno real, fecha de vencimiento y dependencias            |

## 8. Recomendaciones para el motor de triaje

1. Evaluar primero evidencia de seguridad, disponibilidad, alcance e impacto, antes de interpretar expresiones de urgencia.
2. Separar severidad, componente y equipo responsable como decisiones independientes.
3. Priorizar las señales de exposición de información, especialmente accesos entre tenants y fallos de autorización.
4. Utilizar categorías normalizadas de síntomas para generar claves de duplicados consistentes.
5. Registrar evidencia y nivel de confianza de cada clasificación, diferenciando hechos confirmados de hipótesis.
6. Recalcular el SLA cuando se confirme un cambio de severidad, mediante una política explícita sobre el inicio del plazo.
7. Corregir el cálculo de minutos hábiles de P2 y P3 en `evaluate_sla_status`, ya que actualmente contabiliza tiempo calendario a pesar de `operates_24x7=False`.

En particular, `consistency_ratio` no debe interpretarse automáticamente como confianza en la clasificación: la consistencia entre ejecuciones y la certeza sustentada en evidencias son conceptos diferentes.

## 9. Conclusión

La corrección principal del motor consiste en sustituir la clasificación basada en palabras de urgencia por una evaluación estructurada de impacto y riesgo.

INC-1002 e INC-1009 no justifican P0 con la evidencia disponible. INC-1007 merece atención prioritaria porque una posible exposición de facturas entre organizaciones representa un riesgo de seguridad que el clasificador actual parece subestimar.

La clasificación propuesta debe tratarse como una línea base auditable, sujeta a validación con reportes completos, telemetría y registros de seguridad antes de incorporarse como política definitiva.