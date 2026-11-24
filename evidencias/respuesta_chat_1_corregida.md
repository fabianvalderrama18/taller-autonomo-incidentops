Revisión con el JSON completo

Con los reportes completos, la severidad debe basarse en impacto real, alcance observado, disponibilidad y seguridad. Las expresiones de urgencia del usuario no alteran por sí mismas la severidad. Para P0 considero una indisponibilidad crítica y ampliamente confirmada o una exposición de seguridad crítica activa; P1 corresponde a una degradación grave de un servicio crítico o riesgo operativo inmediato; P2 a afectaciones funcionales o de rendimiento acotadas; y P3 a degradaciones menores, cambios cosméticos o riesgos preventivos sin impacto actual.

Clasificación revisada
1. INC-1001
   severity: P0
   component: payments-gateway
   recommended_team: Backend-Core
   duplicate_group_key: payments-gateway:card_payment_unavailable
   Justificación: El reporte confirma HTTP 502 en todas las transacciones con tarjeta durante 12 minutos y afirma que ningún comercio puede cobrar. Hay indisponibilidad general de una función crítica de negocio; “URGENTE” no es necesario para justificar P0.   sample_incidents(1)
2. INC-1002
   severity: P2
   component: auth-identity
   recommended_team: Security-IAM
   duplicate_group_key: auth-identity:account_lockout
   Justificación: La cuenta del usuario está efectivamente bloqueada después de tres intentos, por lo que existe pérdida completa de acceso para ese usuario. No hay evidencia de que otros usuarios o el sistema de autenticación completo estén afectados. La necesidad de acceder “hoy mismo” no eleva la severidad.   sample_incidents(1)
3. INC-1003
   severity: P2
   component: reporting-api
   recommended_team: Backend-Core
   duplicate_group_key: reporting-api:large_dataset_latency
   Justificación: El dashboard tarda aproximadamente 4,5 segundos cuando existen más de 10.000 órdenes. El propio reporte aclara que no se produce error; se trata de degradación de rendimiento asociada a volúmenes altos, no de indisponibilidad.   sample_incidents(1)
4. INC-1004
   severity: P3
   component: frontend-ui
   recommended_team: Backend-Core
   duplicate_group_key: frontend-ui:cosmetic_visibility_request
   Justificación: Es una solicitud de cambio de color del botón de exportación por visibilidad en un monitor. No se reporta fallo funcional, pérdida de disponibilidad ni riesgo de seguridad.   sample_incidents(1)
5. INC-1005
   severity: P1
   component: database-cluster
   recommended_team: Data-DBA
   duplicate_group_key: database-cluster:connection_saturation
   Justificación: El nodo primario de PostgreSQL alcanza 94% de uso de conexiones y ya existen timeouts intermitentes en el pool utilizado por facturación. No es solamente un riesgo teórico: existe degradación observable en un servicio de negocio. Es P1 porque el impacto es grave pero el reporte no indica una caída total de facturación ni del clúster.   sample_incidents(1)
6. INC-1006
   severity: P1
   component: payments-gateway
   recommended_team: Backend-Core
   duplicate_group_key: payments-gateway:card_payment_unavailable
   Justificación: Los clientes de la organización reciben HTTP 502 al intentar pagar y la pasarela se describe como caída. Es una interrupción de una función crítica, pero este reporte por sí solo únicamente confirma el alcance sobre los clientes del reportante; no dice que todos los comercios estén afectados como sí lo hace INC-1001.   sample_incidents(1)
7. INC-1007
   severity: P0
   component: reporting-api
   recommended_team: Security-IAM
   duplicate_group_key: reporting-api:cross_tenant_invoice_exposure
   Justificación: Modificando company_id se pueden visualizar facturas pertenecientes a otra organización. Es una vulneración confirmada del aislamiento entre organizaciones y de la confidencialidad de datos. Que el servicio siga disponible no reduce el impacto de seguridad.   sample_incidents(1)
8. INC-1008
   severity: P2
   component: reporting-api
   recommended_team: Backend-Core
   duplicate_group_key: reporting-api:large_dataset_latency
   Justificación: El listado de planes e historial tarda más de 3 segundos cada vez que se abre para clientes corporativos con más de 10.000 registros. Es una degradación reproducible de rendimiento condicionada al volumen de datos, sin error ni indisponibilidad reportada.   sample_incidents(1)
9. INC-1009
   severity: P3
   component: reporting-api
   recommended_team: Backend-Core
   duplicate_group_key: reporting-api:export_latency
   Justificación: La exportación tarda aproximadamente 20 segundos, pero el reporte confirma explícitamente que finalmente descarga el archivo completo. Por tanto, no existe fallo de exportación ni pérdida funcional demostrada; hay únicamente latencia. El cierre contable de “hoy” y la preocupación de que pueda fallar posteriormente no convierten una ejecución exitosa en P0 o P1.   sample_incidents(1)
10. INC-1010
    severity: P3
    component: infra-certificates
    recommended_team: Platform-SRE
    duplicate_group_key: infra-certificates:certificate_expiry_risk
    Justificación: El certificado pertenece explícitamente a staging y vence dentro de 14 días. Requiere una rotación programada, pero no existe expiración actual ni impacto reportado sobre producción.   sample_incidents(1)
Correcciones respecto a mi respuesta anterior

En INC-1002 indiqué correctamente que el alcance conocido era individual, pero omití un hecho importante del reporte: la cuenta ya aparece bloqueada. No es simplemente una serie de intentos fallidos de autenticación. Por eso cambio también la categoría de duplicado a auth-identity:account_lockout. Lo que continúa sin estar demostrado es una afectación general del servicio de identidad.   sample_incidents(1)

En INC-1005 fui demasiado cauteloso al tratar la saturación como algo que necesitaba todavía métricas de confirmación. El reporte ya proporciona una métrica concreta, 94% de conexiones, y un efecto operacional concreto: timeouts intermitentes en facturación. Mantengo P1, pero ahora la clasificación está sustentada directamente por esos dos hechos y no por una posible saturación hipotética.   sample_incidents(1)

En INC-1007 la conclusión P0 era correcta, pero ahora puede expresarse sin ninguna suposición: el reporte dice explícitamente que cambiar company_id permite visualizar facturas de otra organización. No hace falta inferir una posible fuga; el acceso cross-tenant ya está descrito como reproducible.   sample_incidents(1)

La corrección más significativa es INC-1009. Mi respuesta anterior habló de una exportación “bloqueada o que no termina” y eso contradice el JSON. El archivo sí se genera y se descarga completo después de unos 20 segundos. Por esa razón cambio la clasificación de P2 a P3 y el duplicate_group_key de una categoría de bloqueo a reporting-api:export_latency.   sample_incidents(1)

Agrupación de duplicados

INC-1001 e INC-1006 comparten payments-gateway:card_payment_unavailable porque ambos presentan el mismo componente y el mismo síntoma operacional: los pagos con tarjeta no pueden completarse y el usuario recibe HTTP 502. Esto no obliga a asignarles la misma severidad. INC-1001 confirma un alcance mucho mayor, “todas las transacciones” y “ningún comercio”, mientras INC-1006 solamente confirma afectación para los clientes de la organización que reporta.   sample_incidents(1)   sample_incidents(1)

INC-1003 e INC-1008 comparten reporting-api:large_dataset_latency porque ambos describen latencia reproducible cuando el volumen supera 10.000 registros. Cambia la operación concreta —dashboard histórico frente a listado de planes e historial—, pero componente, condición y categoría observable del síntoma coinciden.   sample_incidents(1)   sample_incidents(1)

Información realmente faltante

INC-1001 ya informa duración, error, tipo de transacción y alcance general. Falta principalmente la causa técnica, regiones o dependencias afectadas y si existe un método alternativo de cobro.

INC-1002 ya informa que la cuenta está bloqueada y que el problema sigue tres intentos. Falta saber la causa del bloqueo, si es comportamiento esperado de la política de seguridad, si existe mecanismo de desbloqueo y si hay más usuarios afectados.

INC-1003 ya informa latencia aproximada, condición de más de 10.000 órdenes y ausencia de errores. Falta el SLO o baseline esperado y el porcentaje de clientes que cumplen esa condición.

INC-1005 ya informa 94% de utilización y timeouts intermitentes en facturación. Falta la duración y tendencia de la saturación, tasa de timeouts, capacidad restante, estado de réplicas y si otros servicios comparten el mismo pool o clúster.

INC-1006 ya informa HTTP 502 y bloqueo de pagos para los clientes del reportante. Falta conocer si otras organizaciones están experimentando el mismo episodio y si corresponde exactamente a la misma ocurrencia operacional de INC-1001.

INC-1007 ya confirma el mecanismo de acceso cross-tenant. Falta saber qué campos contienen las facturas, cuántas organizaciones pueden verse afectadas, desde cuándo existe la vulnerabilidad, si fue explotada previamente y si ya se aplicó contención.

INC-1008 ya informa la condición de más de 10.000 registros y latencia superior a 3 segundos. Falta el tiempo normal esperado, la distribución de latencias y el alcance entre organizaciones.

INC-1009 ya informa tanto la duración, aproximadamente 20 segundos, como el resultado exitoso y completo de la descarga. No falta saber si termina: eso ya está explícitamente resuelto. Falta determinar cuál es el tiempo normal/SLO, tamaño de la exportación y si los 20 segundos representan una regresión real o un rendimiento esperado.

INC-1010 ya informa entorno, plazo de expiración y necesidad de rotación. Falta conocer si la renovación está automatizada y si el certificado de staging comparte algún recurso o cadena relevante con producción.

Con los datos completos, los tres errores de triaje más claros del clasificador actual son INC-1002 elevado indebidamente por urgencia temporal, INC-1007 subestimado pese a una exposición cross-tenant confirmada e INC-1009 elevado pese a que la operación termina correctamente.
