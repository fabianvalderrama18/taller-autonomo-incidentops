---
name: bdd-acceptance
description: Redacta escenarios BDD Given/When/Then estilo Dan North con vocabulario ubicuo de negocio y los mapea 1:1 a funciones test_bdd_* con TestClient (FastAPI) y CliRunner (Typer) sobre almacenamiento aislado. Úsala al escribir o revisar specs y pruebas de aceptación de un hito.
---

# Aceptación BDD — IncidentOps

## 1. Redacción del escenario en `spec.md`

- Un escenario describe **un único comportamiento observable**, con título como frase de negocio en estilo Dan North: «Cuenta individual bloqueada mencionando "hoy"», no «Prueba de classify_incident_report».
- Escribe `Given / When / Then` en voz activa y en pasado, con el **vocabulario ubicuo del negocio**: incidente, reporte, triaje, severidad, equipo recomendado, clave de duplicados, revisión humana, vencimiento del SLA.
- **No filtres nombres de implementación** en el escenario: ni clases o módulos Python (`IncidentService`, `TriageResult`), ni tablas o columnas SQL, ni detalles de transporte (rutas HTTP, JSON, códigos de salida). Esos detalles pertenecen a un bloque aparte «Detalle técnico (adaptador)» o a la prueba.
- Cada escenario es independiente, ejecutable y verificable: `Then` afirma un resultado observable, no una intención («debe clasificar» → «la respuesta indica severidad P2 y equipo Security-IAM»).
- En este repositorio el `spec.md` del hito es `specs/001-triage-endpoint-manual.md`.

Plantilla:

```markdown
### Escenario — <frase de negocio>

**Given** <contexto de negocio>
**When** <acción del usuario o del sistema>
**Then** <resultado observable en lenguaje de negocio>

**Detalle técnico (adaptador)**: endpoint, cuerpo, JSON esperado o código de salida.
```

## 2. Mapeo 1:1 con pruebas

- **Un escenario = una función `test_bdd_*`** en `tests/`. El sufijo es el slug del título del escenario. No agrupes varios escenarios en una misma función ni dejes un escenario sin prueba.
- La **docstring** de la función reproduce el `Given / When / Then` para mantener la trazabilidad con la spec.
- La prueba afirma solo lo descrito en `Then`: salida observable y efectos acordados. No comprueba llamadas internas, nombres de clases ni estructura de base de datos.
- Si el escenario exige **paridad entre adaptadores primarios**, la misma función `test_bdd_*` ejercita REST con `fastapi.testclient.TestClient` y CLI con `typer.testing.CliRunner`, y compara el resultado observable. No dupliques el escenario en la spec por cada canal salvo que el comportamiento esperado sea distinto.
- Parametriza solo los ejemplos que la spec enumera explícitamente; cada caso parametrizado corresponde a un ejemplo documentado.

Esqueleto:

```python
def test_bdd_<slug>(client, runner, canonical_reports):
    """Given ... / When ... / Then ..."""
    # When: canal HTTP (TestClient) y, si aplica, canal CLI (CliRunner)
    # Then: aserciones sobre el resultado observable
```

## 3. Almacenamiento aislado

- `tests/conftest.py` entrega **fixtures frescas por prueba**: `TestClient(create_app())` para HTTP y `CliRunner()` para CLI. Ninguna prueba reutiliza cliente, app ni runner de otra.
- Los reportes canónicos se leen de `data/sample_incidents.json` **solo en lectura**; no se mutan ni se comparten entre pruebas.
- H001 es stateless: no hay base de datos. Al introducir persistencia, cada prueba recibe su **propia BD temporal o en memoria**, construida a través de `src.adapters.outbound.factory`; nunca se comparte conexión ni se siembra una BD global.
- Toda modificación de estado se crea y se descarta dentro de la misma prueba.

## 4. Checklist antes de cerrar un hito

1. ¿Cada escenario de la spec usa lenguaje de negocio y un solo `Then` verificable?
2. ¿Existe exactamente una función `test_bdd_*` por escenario, con el `Given / When / Then` en su docstring?
3. ¿La prueba usa `TestClient` y/o `CliRunner` y solo afirma resultados observables?
4. ¿Las fixtures son frescas y no hay estado compartido?
5. ¿Pasa `uv run pytest -v`?
