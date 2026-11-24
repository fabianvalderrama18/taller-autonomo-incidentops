"""Validación de transporte del instante de referencia (FR-008, FR-009).

HTTP y CLI comparten esta función para que la interpretación del parámetro no
pueda divergir. No contiene reglas de negocio: solo exige ISO naive estricto.
"""

from datetime import datetime
import re

_ISO_NAIVE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


def parse_reference_time(value: str | None) -> datetime | None:
    """Devuelve un `datetime` naive o lanza `ValueError` si el formato es inválido."""
    if value is None:
        return None
    if not _ISO_NAIVE.fullmatch(value):
        raise ValueError(
            "reference_time debe tener el formato YYYY-MM-DDTHH:MM:SS sin zona horaria"
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("reference_time no es una fecha válida") from exc
    if parsed.tzinfo is not None:
        raise ValueError("reference_time no debe incluir zona horaria")
    return parsed


def parse_lifecycle_time(value: str | None) -> datetime | None:
    """Acepta fecha y hora ISO con offset opcional; dominio normaliza la zona."""
    if value is None:
        return None
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})?",
        value,
    ):
        raise ValueError("Fecha inválida: se requiere fecha y hora ISO 8601")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
