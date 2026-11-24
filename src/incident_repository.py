"""Compatibilidad: el repositorio vive en `src.adapters.outbound.incident_repository`."""

from src.adapters.outbound.incident_repository import IncidentRepository, _run_benchmark

__all__ = ["IncidentRepository"]

if __name__ == "__main__":
    _run_benchmark()
