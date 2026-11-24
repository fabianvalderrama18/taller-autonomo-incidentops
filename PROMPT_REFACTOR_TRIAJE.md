Prompt de referencia proporcionado en la conversación de trabajo para la refactorización del Reto 1. Se conserva el contexto inicial y las instrucciones operativas. La respuesta del chat externo está en evidencias/respuesta_refactor_triaje.md; este archivo no es una exportación del historial de ese chat.

<role>
Actúa como ingeniero Python encargado de corregir el motor determinista de triaje de IncidentOps. Necesito una solución clara, verificable y proporcionada al alcance del taller.
</role>
<context>
Estoy desarrollando el Reto 1 de IncidentOps. Ya comparé dos consultas independientes y contrasté sus respuestas con los reportes completos.
Adjunto sample_incidents.json con los 10 reportes completos y models.py con las entidades originales, imports, alias y decoradores que deben conservarse.
Confirma que puedes leer ambos archivos. Si alguno no está disponible, indícalo antes de generar código.
El bloque siguiente fue extraído mediante src.context_audit, que usa AST para simular LSP. No representa un archivo Python completo.
<lsp_context symbol="classify_incident_report">
  <!-- 1. Definiciones de Tipos y Políticas (LSP Hover / Type Definition) -->
# [LSP textDocument/hover type] src/models.py:12
class SLARule:
    """Define el acuerdo de nivel de servicio (SLA) para un nivel de severidad."""

    severity: SeverityLevel
    max_resolution_minutes: int
    operates_24x7: bool
    escalation_threshold_ratio: float = 0.75

# [LSP textDocument/hover type] src/models.py:22
class Incident:
    """Representa un incidente registrado en la plataforma IncidentOps."""

    incident_id: str
    title: str
    component: str
    severity: SeverityLevel
    status: IncidentStatus
    created_at: datetime
    resolved_at: Optional[datetime] = None

# [LSP textDocument/hover type] src/models.py:35
class SLAEvaluation:
    """Resultado determinista de la evaluación de SLA de un incidente."""

    incident_id: str
    severity: SeverityLevel
    elapsed_minutes: int
    allowed_minutes: int
    remaining_minutes: int
    is_breached: bool
    requires_escalation: bool

# [LSP textDocument/hover type] src/models.py:48
class TriageResult:
    """Resultado estructurado producido por el clasificador de triaje con IA."""

    incident_id: str
    severity: SeverityLevel
    component: str
    rationale: str
    consistency_ratio: float = 1.0

# [LSP textDocument/hover symbol] src/sla_calculator.py:17
SLA_POLICY_TABLE: Dict[SeverityLevel, SLARule] = {
    "P0": SLARule(severity="P0", max_resolution_minutes=60, operates_24x7=True),
    "P1": SLARule(severity="P1", max_resolution_minutes=240, operates_24x7=True),
    "P2": SLARule(severity="P2", max_resolution_minutes=480, operates_24x7=False),
    "P3": SLARule(severity="P3", max_resolution_minutes=1440, operates_24x7=False),
}

  <!-- 2. Definición Exacta del Símbolo (LSP GoToDefinition) -->
# [LSP textDocument/definition] src/triage_rules.py:27
def classify_incident_report(incident_id: str, raw_text: str) -> TriageResult:
    """Clasifica un reporte de incidente aplicando reglas heurísticas iniciales.

    DEUDA TÉCNICA INTENCIONAL:
    - Evalúa palabras sueltas ("hoy", "urgente") antes de analizar el impacto real
      (caída global vs. cuenta individual vs. entorno de staging).
    - No normaliza componentes ni identifica el equipo de guardia correspondiente.
    """
    text_lower = raw_text.lower()

    # Bug de diseño: si un usuario dice "necesito acceder hoy" por su cuenta bloqueada,
    # se dispara como P0 antes de verificar si es una caída global o un caso individual.
    if "urgente" in text_lower or "hoy" in text_lower or "502" in text_lower:
        severity: SeverityLevel = "P0"
    elif "94%" in text_lower or "timeout" in text_lower:
        severity = "P1"
    elif "lenta" in text_lower or "segundos" in text_lower:
        severity = "P2"
    else:
        severity = "P3"

    if "pago" in text_lower or "cobro" in text_lower or "tarjeta" in text_lower:
        component = "payments-gateway"
    elif "cuenta" in text_lower or "ingresar" in text_lower:
        component = "auth-identity"
    elif "postgresql" in text_lower or "conexiones" in text_lower:
        component = "database-cluster"
    elif "certificado" in text_lower or "tls" in text_lower:
        component = "infra-certificates"
    elif "botón" in text_lower or "color" in text_lower:
        component = "frontend-ui"
    else:
        component = "reporting-api"

    return TriageResult(
        incident_id=incident_id,
        severity=severity,
        component=component,
        rationale=f"Clasificación heurística legacy asignada a {component} ({severity}).",
    )

  <!-- 3. Referencias de Invocación en el Proyecto (LSP FindReferences) -->
# [LSP textDocument/references] src/triage_rules.py:77
  L76:     for item in incidents:
  L77:         result = classify_incident_report(item["id"], item["raw_text"])
  L78:         snippet = item["raw_text"][:45] + "..." if len(item["raw_text"]) > 45 else item["raw_text"]
</lsp_context>
El módulo debe cargar data/sample_incidents.json resolviendo la ruta respecto al proyecto mediante pathlib.
</context>
<domain_rules>
P0: indisponibilidad generalizada de pagos o exposición de facturas entre organizaciones por fallo de autorización.
P1: interrupción de pagos limitada al comercio reportante o saturación de conexiones acompañada de timeouts.
P2: bloqueo individual de cuenta y degradaciones de rendimiento, incluidas exportaciones lentas que terminan correctamente.
P3: solicitudes cosméticas y mantenimiento preventivo de certificados de staging sin afectación actual.
Las palabras hoy y urgente no determinan severidad; un 502 aislado tampoco demuestra alcance generalizado ni identifica pagos.
Backend-Core atiende pagos, reportes e interfaz; Platform-SRE infraestructura y certificados; Data-DBA bases de datos; Security-IAM autenticación, autorización y exposición de información.
El componente de la exposición de facturas es reporting-api y su equipo Security-IAM.
La clave tiene formato component:symptom_category. INC-1001/INC-1006 deben compartir clave, igual que INC-1003/INC-1008. Compartir clave no exige igual severidad ni demuestra causa raíz común.
INC-1002 tiene la cuenta bloqueada; INC-1005 informa 94% de conexiones y timeouts; INC-1007 describe acceso a facturas ajenas; INC-1009 descarga el archivo completo tras 20 segundos.
</domain_rules>
<examples>
Todas las transacciones con tarjeta devuelven HTTP 502 y ningún comercio puede cobrar: P0, payments-gateway, Backend-Core, payments-gateway:payment_http_502.
A nuestros clientes les sale error 502 al pagar: P1, payments-gateway, Backend-Core, payments-gateway:payment_http_502. Misma categoría, diferente alcance.
Dashboard de 4,5 segundos con más de 10.000 órdenes y listado de más de 3 segundos con más de 10.000 registros: ambos P2, reporting-api, Backend-Core, reporting-api:large_dataset_latency.
Cambiar company_id permite visualizar facturas de otra organización: P0, reporting-api, Security-IAM, reporting-api:cross_tenant_data_exposure.
Excel tarda 20 segundos y descarga el archivo completo: P2, reporting-api, Backend-Core, reporting-api:export_latency. No es una exportación fallida.
</examples>
<constraints>
Mantén classify_incident_report(incident_id: str, raw_text: str) -> TriageResult.
Conserva entidades y campos originales; añade recommended_team y duplicate_group_key respetando el orden de dataclasses.
No clasifiques por ID ni uses una tabla de respuestas dentro del clasificador; los IDs solo pueden identificar expectativas de pruebas.
Utiliza biblioteca estándar y reglas deterministas. Normaliza mayúsculas, espacios y acentos cuando sea necesario.
Define un respaldo explícito y documenta sus limitaciones.
Conserva consistency_ratio por compatibilidad sin presentarlo como confianza medida.
No modifiques sla_calculator.py ni incident_repository.py.
</constraints>
<task>
Presenta brevemente las reglas y su precedencia. Entrega models.py y triage_rules.py completos.
El punto de entrada debe leer los 10 reportes y mostrar ID, severidad, componente, equipo, clave y justificación. Verifica los resultados y termina con error si falla una comprobación.
Severidades esperadas de INC-1001 a INC-1010: P0, P2, P2, P3, P1, P1, P0, P2, P2, P3.
Comprueba equipos, componentes y parejas de duplicados.
Prueba que hoy/urgente no elevan un caso individual, un 502 ajeno a pagos no se clasifica como pagos, cambiar el ID no modifica la clasificación y la exportación exitosa no se describe como fallida.
Incluye uv run python -m src.triage_rules y distingue pruebas realmente ejecutadas de resultados esperados.
</task>
