"""Compatibilidad: el cálculo vive en `src.domain.sla_calculator`."""

from src.domain.sla_calculator import (
    SLA_POLICY_TABLE,
    _run_demo,
    evaluate_sla_status,
    get_sla_rule_for_severity,
)

__all__ = [
    "SLA_POLICY_TABLE",
    "evaluate_sla_status",
    "get_sla_rule_for_severity",
]

if __name__ == "__main__":
    _run_demo()
