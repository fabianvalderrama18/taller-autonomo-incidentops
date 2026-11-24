Voy a separar la clasificación en reglas observables y decisiones por incidente, evitando usar palabras de urgencia como señal de severidad. Donde el extracto no permita confirmar alcance o causa, lo marcaré como ambigüedad en vez de rellenar huecos.

Criterios propuestos

Severidad:\
P0: interrupción activa de una capacidad crítica con alcance amplio o multi-organización, o incidente de seguridad crítico confirmado, como exposición activa de datos entre organizaciones. La severidad se justifica por impacto real, alcance, confidencialidad/integridad o indisponibilidad; no por palabras como “urgente”, “hoy” o “necesito”.

P1: degradación grave de una capacidad crítica de producción, riesgo alto e inmediato de indisponibilidad o integridad, o incidente de seguridad importante pero contenido. Debe existir evidencia de impacto significativo o riesgo técnico concreto.

P2: afectación limitada a usuarios, una organización o una funcionalidad no crítica; degradación de rendimiento; función secundaria no disponible; o problema importante pero sin evidencia de afectación general del servicio.

P3: problemas cosméticos, solicitudes de mejora, incidencias de entorno no productivo o defectos con impacto operativo bajo.

Componente:\
Debe representar el sistema donde se manifiesta o se origina razonablemente el síntoma, utilizando evidencia del reporte. Un problema de seguridad no obliga a cambiar el componente técnico: por ejemplo, una fuga causada por reporting-api sigue perteneciendo a reporting-api aunque el equipo recomendado sea Security-IAM.

Equipo:\
Backend-Core: lógica de aplicación, APIs, frontend y servicios de negocio.\
Platform-SRE: infraestructura, certificados, disponibilidad de plataforma y operación.\
Data-DBA: motores de base de datos, almacenamiento, replicación y rendimiento del clúster.\
Security-IAM: autenticación, autorización, aislamiento entre organizaciones y respuesta ante exposición de información.

Duplicados:\
La clave debe describir componente y categoría estable del síntoma, no palabras específicas del reporte ni su severidad. Formato obligatorio: component:symptom_category.

Clasificación propuesta

ID: INC-1001\
severity: P0\
component: payments-gateway\
recommended_team: Backend-Core\
duplicate_group_key: payments-gateway:payment_processing_unavailable\
Justificación: El reporte indica respuestas HTTP 5xx del gateway de pagos. Eso representa indisponibilidad de una función crítica de negocio. La palabra “URGENTE” no participa en la clasificación. El alcance exacto no aparece en el extracto, por lo que P0 presupone que la falla afecta de forma general el procesamiento de pagos.

ID: INC-1002\
severity: P2\
component: auth-identity\
recommended_team: Security-IAM\
duplicate_group_key: auth-identity:user_authentication_failure\
Justificación: El hecho verificable es que un usuario informa varios intentos fallidos de acceso a su cuenta. No hay evidencia en el extracto de caída general de autenticación ni de múltiples organizaciones afectadas. Un caso individual no debe convertirse en P0 por expresiones de urgencia temporal.

ID: INC-1003\
severity: P2\
component: reporting-api\
recommended_team: Backend-Core\
duplicate_group_key: reporting-api:reporting_latency\
Justificación: Se reporta lentitud en consultas o visualización de reportes históricos. El servicio aparentemente responde, pero con rendimiento degradado. No existe evidencia de indisponibilidad general ni impacto de seguridad.

ID: INC-1004\
severity: P3\
component: frontend-ui\
recommended_team: Backend-Core\
duplicate_group_key: frontend-ui:ui_cosmetic_request\
Justificación: El reporte solicita un cambio visual de color. Es una mejora cosmética y no representa degradación de disponibilidad, seguridad o funcionalidad.

ID: INC-1005\
severity: P1\
component: database-cluster\
recommended_team: Data-DBA\
duplicate_group_key: database-cluster:primary_db_resource_saturation\
Justificación: El reporte señala utilización elevada en el nodo primario de PostgreSQL. Al tratarse del primario, una saturación significativa puede afectar una dependencia crítica de producción. P1 es razonable si existen métricas que confirmen saturación sostenida o degradación; sin esas métricas, P2 también sería defendible.

ID: INC-1006\
severity: P0\
component: payments-gateway\
recommended_team: Backend-Core\
duplicate_group_key: payments-gateway:payment_processing_unavailable\
Justificación: El reporte señala nuevamente una caída de la pasarela de cobros con tarjeta. Es el mismo tipo de incapacidad funcional que INC-1001 y afecta una capacidad crítica de pagos.

ID: INC-1007\
severity: P0\
component: reporting-api\
recommended_team: Security-IAM\
duplicate_group_key: reporting-api:cross_tenant_invoice_exposure\
Justificación: Existe exposición de facturas entre organizaciones mediante manipulación del parámetro de compañía. Es un fallo de aislamiento entre tenants y una exposición activa de información, por lo que el impacto de seguridad domina la clasificación aunque la API permanezca disponible. La clasificación anterior P3 subestima materialmente el incidente.

ID: INC-1008\
severity: P2\
component: reporting-api\
recommended_team: Backend-Core\
duplicate_group_key: reporting-api:reporting_latency\
Justificación: El reporte describe tiempos elevados en el listado de planes e historial. Es degradación de rendimiento de reporting-api, sin evidencia de caída completa o incidente de seguridad.

ID: INC-1009\
severity: P2\
component: reporting-api\
recommended_team: Backend-Core\
duplicate_group_key: reporting-api:excel_export_stall\
Justificación: La exportación mensual a Excel queda bloqueada o no termina. Es una función específica afectada, pero el extracto no demuestra indisponibilidad completa de reporting-api ni afectación generalizada. Que el usuario necesite el archivo “hoy”, si esa expresión aparece en el reporte completo, no convierte el incidente en P0.

ID: INC-1010\
severity: P3\
component: infra-certificates\
recommended_team: Platform-SRE\
duplicate_group_key: infra-certificates:staging_tls_certificate_expiry\
Justificación: El certificado corresponde al entorno de staging. No existe evidencia en el extracto de impacto sobre producción. Debe corregirse antes del vencimiento, pero su impacto operativo actual es bajo.

Revisión específica de INC-1002, INC-1007 e INC-1009

INC-1002 es el ejemplo más claro de por qué el lenguaje del usuario no debe controlar la severidad. “He intentado ingresar tres veces” acredita un problema de autenticación para esa persona, pero no demuestra una caída del sistema de identidad. Con los datos disponibles corresponde P2. Subiría a P1 o P0 solamente con evidencia adicional de alcance, por ejemplo un porcentaje significativo de usuarios incapaces de autenticarse.

INC-1007 es el caso inverso. Puede no existir indisponibilidad, pero sí un impacto de seguridad crítico. La exposición de facturas de una organización a otra rompe el aislamiento de tenants y afecta confidencialidad. Si la exposición es reproducible y está activa, P0 es apropiado aunque solo se haya descubierto inicialmente con una cuenta.

INC-1009 tampoco debe elevarse por presión temporal del solicitante. Una exportación que se queda procesando es un fallo funcional real, por lo que P2 es más adecuado que P3, pero no existe evidencia para P0. Su severidad aumentaría si la exportación fuese un proceso regulatorio crítico, afectara a todas las organizaciones o bloqueara un cierre financiero sin alternativa.

Agrupación de duplicados

INC-1001 e INC-1006 deben compartir payments-gateway:payment_processing_unavailable porque ambos describen la misma manifestación operacional: la pasarela no permite procesar cobros normalmente. Que un reporte mencione HTTP 5xx y otro diga que “cayó la pasarela” no justifica grupos distintos. La causa raíz puede terminar siendo diferente; la clave propuesta agrupa por componente y categoría observable del síntoma, no por una causa todavía no demostrada.

INC-1003 e INC-1008 deben compartir reporting-api:reporting_latency porque ambos describen respuestas anormalmente lentas dentro de reporting-api. Que uno mencione reportes históricos y otro planes/historial puede utilizarse posteriormente como dimensión diagnóstica, pero no cambia la categoría principal del síntoma. Si la investigación demostrara rutas, dependencias o causas completamente independientes, podrían separarse posteriormente.

Decisiones ambiguas e información faltante

INC-1001: falta conocer porcentaje de transacciones fallidas, duración, regiones u organizaciones afectadas y existencia de métodos de pago alternativos. Sin alcance amplio confirmado, podría ser P1 en lugar de P0.

INC-1002: faltan otros usuarios afectados, errores concretos de autenticación, estado del proveedor de identidad y si existe bloqueo de cuenta. La evidencia disponible solamente permite afirmar afectación individual.

INC-1003 e INC-1008: faltan latencias normales y actuales, percentiles, endpoints concretos, número de organizaciones afectadas y presencia de timeouts. Esto permitiría distinguir P2 de una degradación P1.

INC-1005: faltan porcentaje de CPU/memoria/IO, duración de la saturación, réplicas disponibles, lag de replicación, latencia de consultas y efecto visible en aplicaciones. Es la clasificación más discutible después de los tres casos destacados.

INC-1007: deben confirmarse qué campos de factura quedan expuestos, si cualquier tenant puede explotarlo, desde cuándo existe, accesos históricos, cantidad de organizaciones potencialmente afectadas y si la exposición ya fue contenida. Estos datos no son necesarios para reconocer el incidente de seguridad, pero sí para determinar su alcance y respuesta.

INC-1009: falta determinar si afecta a un usuario, una organización o todas; si fallan todas las exportaciones; si existe alternativa CSV/API; y si la exportación es necesaria para una obligación financiera o regulatoria. Con la evidencia actual, P2 es una clasificación provisional.

INC-1010: debe confirmarse que el certificado pertenece exclusivamente a staging y que no comparte infraestructura, dominio o cadena de certificados con producción.

La corrección conceptual principal del motor sería que severidad se derive de impacto + alcance + seguridad + disponibilidad, mientras que términos como “urgente”, “hoy”, “ya” o número de intentos solo pueden aportar contexto. Además, los incidentes de confidencialidad entre organizaciones necesitan reglas explícitas de alta severidad aunque no exista una caída del servicio.