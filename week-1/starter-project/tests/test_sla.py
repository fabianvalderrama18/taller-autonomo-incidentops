"""Casos de frontera y oráculo independiente para SLA."""
import random
import unittest
from datetime import datetime, timedelta, timezone
from src.models import Incident
from src.sla_calculator import evaluate_sla_status


class SLATests(unittest.TestCase):
    def incident(self, severity='P2', start=None, status='OPEN', resolved=None):
        return Incident('TEST', 'Prueba', 'reporting-api', severity, status,
                        start or datetime(2026, 11, 9, 8), resolved)

    def test_all_severity_thresholds(self):
        for severity, allowed in [('P0',60),('P1',240),('P2',480),('P3',1440)]:
            # Convierte minutos consumidos a referencia con un oráculo minuto a minuto.
            for consumed in [int(allowed*.75)-1, int(allowed*.75), allowed, allowed+1]:
                with self.subTest(severity=severity, consumed=consumed):
                    incident=self.incident(severity)
                    end=incident.created_at
                    counter=0
                    while counter<consumed:
                        if severity in ('P0','P1') or (end.weekday()<5 and 8<=end.hour<18):
                            counter+=1
                        end+=timedelta(minutes=1)
                    result=evaluate_sla_status(incident,end)
                    self.assertEqual(result.elapsed_minutes,consumed)
                    self.assertEqual(result.is_breached,consumed>allowed)
                    self.assertEqual(result.requires_escalation,consumed>=allowed*.75)
                    self.assertEqual(result.remaining_minutes,allowed-consumed)

    def test_random_intervals_against_minute_oracle(self):
        rng=random.Random(1726)
        for i in range(40):
            start=datetime(2026,11,1)+timedelta(minutes=rng.randrange(14400))
            duration=rng.randrange(1,20000)
            expected=sum(1 for n in range(duration)
                         if (start+timedelta(minutes=n)).weekday()<5
                         and 8<=(start+timedelta(minutes=n)).hour<18)
            with self.subTest(case=i):
                actual=evaluate_sla_status(self.incident(start=start),start+timedelta(minutes=duration))
                self.assertEqual(actual.elapsed_minutes,expected)

    def test_fractional_minutes_accumulate_across_days(self):
        incident=self.incident(start=datetime(2026,11,6,17,59,30))
        result=evaluate_sla_status(incident,datetime(2026,11,9,8,0,30))
        self.assertEqual(result.elapsed_minutes,1)

    def test_one_second_beyond_sla(self):
        incident=self.incident('P0')
        result=evaluate_sla_status(incident,incident.created_at+timedelta(hours=1,seconds=1))
        self.assertTrue(result.is_breached)
        self.assertTrue(result.requires_escalation)

    def test_opening_closing_and_zero_duration(self):
        for start,end,expected in [
            ('2026-11-09T07:00','2026-11-09T08:00',0),
            ('2026-11-09T18:00','2026-11-10T08:00',0),
            ('2026-11-09T08:00','2026-11-09T08:00',0),
            ('2026-11-09T08:00','2026-11-09T18:00',600),
            ('2026-11-07T08:00','2026-11-09T08:00',0),
        ]:
            with self.subTest(start=start,end=end):
                result=evaluate_sla_status(self.incident(start=datetime.fromisoformat(start)),datetime.fromisoformat(end))
                self.assertEqual(result.elapsed_minutes,expected)

    def test_resolution_stops_clock_and_escalation(self):
        for status in ['RESOLVED','OPEN']:
            incident=self.incident('P0', status=status,resolved=datetime(2026,11,9,10))
            result=evaluate_sla_status(incident,datetime(2026,11,20))
            self.assertEqual(result.elapsed_minutes,120)
            self.assertTrue(result.is_breached)
            self.assertFalse(result.requires_escalation)

    def test_resolved_status_without_timestamp(self):
        result=evaluate_sla_status(self.incident('P0',status='RESOLVED'),datetime(2026,11,9,10))
        self.assertFalse(result.requires_escalation)
        self.assertEqual(result.elapsed_minutes,120)

    def test_escalated_status_keeps_flag(self):
        result=evaluate_sla_status(self.incident('P0',status='ESCALATION_REQUIRED'),datetime(2026,11,9,10))
        self.assertTrue(result.requires_escalation)

    def test_invalid_interval_or_severity(self):
        for incident,end in [
            (self.incident(),datetime(2026,11,8)),
            (self.incident(resolved=datetime(2026,11,8)),datetime(2026,11,10)),
            (self.incident('P9'),datetime(2026,11,10))
        ]:
            with self.subTest(incident=incident):
                with self.assertRaises(ValueError): evaluate_sla_status(incident,end)

    def test_explicit_timezone_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sla_status(self.incident(),datetime(2026,11,10,tzinfo=timezone.utc))

    def test_max_date_does_not_overflow(self):
        incident=self.incident(start=datetime(9999,12,31,17))
        self.assertEqual(evaluate_sla_status(incident,datetime(9999,12,31,18)).elapsed_minutes,60)

    def test_resolved_incident_ignores_unused_reference_timezone(self):
        incident = self.incident('P0', resolved=datetime(2026,11,9,9))
        result = evaluate_sla_status(incident, datetime(2026,11,10,tzinfo=timezone.utc))
        self.assertEqual(result.elapsed_minutes, 60)
        self.assertFalse(result.requires_escalation)

    def test_microsecond_after_deadline(self):
        incident = self.incident('P0')
        result = evaluate_sla_status(incident, incident.created_at + timedelta(hours=1,microseconds=1))
        self.assertTrue(result.is_breached)
        self.assertTrue(result.requires_escalation)

    def test_inputs_not_mutated(self):
        incident=self.incident()
        before=vars(incident).copy()
        evaluate_sla_status(incident,datetime(2026,11,10))
        self.assertEqual(vars(incident),before)


if __name__=='__main__': unittest.main()
