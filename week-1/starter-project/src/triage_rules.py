"""Compatibilidad: el clasificador vive en `src.domain.triage_rules`."""

from src.domain.triage_rules import EXPECTED, classify_incident_report, main

__all__ = ["EXPECTED", "classify_incident_report", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
