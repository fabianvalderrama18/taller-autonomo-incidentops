"""Regresiones externas al ejemplo ejecutable del taller."""
import json
import unittest
import unicodedata
from pathlib import Path
from src.triage_rules import classify_incident_report


class TriageRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = json.loads((Path(__file__).resolve().parents[1] / 'data/sample_incidents.json').read_text())

    def signature(self, result):
        return (result.severity, result.component, result.recommended_team,
                result.duplicate_group_key, result.rationale)

    def test_normalization_preserves_all_cases(self):
        for report in self.reports:
            with self.subTest(incident=report['id']):
                text = report['raw_text']
                altered = ''.join(c for c in unicodedata.normalize('NFD', text) if not unicodedata.combining(c))
                altered = '  \n'.join(altered.upper().split())
                self.assertEqual(self.signature(classify_incident_report('A', text)), self.signature(classify_incident_report('B', altered)))

    def test_ids_do_not_control_results(self):
        for report in self.reports:
            with self.subTest(incident=report['id']):
                self.assertEqual(self.signature(classify_incident_report(report['id'], report['raw_text'])), self.signature(classify_incident_report('INC-1007', report['raw_text'])))

    def test_urgency_does_not_control_results(self):
        for report in self.reports:
            with self.subTest(incident=report['id']):
                self.assertEqual(self.signature(classify_incident_report('A', report['raw_text'])), self.signature(classify_incident_report('B', 'URGENTE hoy: ' + report['raw_text'])))

    def test_other_payment_failure_does_not_invent_502(self):
        result = classify_incident_report('X', 'La pasarela de pagos devuelve error 503 al cobrar.')
        self.assertEqual(result.severity, 'P1')
        self.assertEqual(result.duplicate_group_key, 'payments-gateway:payment_unavailable')

    def test_unknown_requires_manual_review(self):
        result = classify_incident_report('X', 'El servicio de notificaciones devuelve HTTP 502.')
        self.assertEqual(result.component, 'unknown-component')
        self.assertIn('revisión manual', result.rationale)

    def test_other_modules_import(self):
        from src.incident_repository import IncidentRepository
        from src.sla_calculator import evaluate_sla_status
        self.assertTrue(callable(evaluate_sla_status))
        repo = IncidentRepository()
        repo.conn.close()


if __name__ == '__main__':
    unittest.main()
