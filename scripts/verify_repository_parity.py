"""Compara todas las operaciones del puerto entre SQLite y PostgreSQL reales."""
from dataclasses import asdict
from datetime import datetime
import os
from uuid import uuid4

from src.adapters.outbound.factory import create_repository
from src.application.ports import IncidentRepositoryPort
from src.domain.models import Incident

url = os.environ['DATABASE_URL']
assert url.startswith('postgresql://'), 'Requiere PostgreSQL real'
postgres = create_repository(url)
sqlite = create_repository('sqlite:///:memory:')
component = 'verify-' + uuid4().hex[:8]
for repo in (sqlite, postgres):
    assert isinstance(repo, IncidentRepositoryPort)
    assert repo.check_health()
    for index, status in enumerate(('OPEN', 'IN_PROGRESS', 'ESCALATION_REQUIRED', 'RESOLVED')):
        item = Incident(f'{component}-{index}', 'Prueba del puerto', component, 'P2', status,
                        datetime(2026, 11, 6, 17), recommended_team='Security-IAM',
                        duplicate_group_key=component + ':account_lockout')
        repo.save_incident(item)
        assert repo.get_incident(item.incident_id) == item
    assert repo.get_incident(component + '-missing') is None
    item = repo.get_incident(component + '-0')
    item.title = 'Actualización verificada'
    repo.save_incident(item)
    assert repo.get_incident(item.incident_id) == item
    duplicates = repo.find_open_duplicates(component + ':account_lockout', component + '-1')
    assert [i.incident_id for i in duplicates] == [component + '-0', component + '-2']
assert [asdict(i) for i in postgres.list_active_incidents(component)] == [asdict(i) for i in sqlite.list_active_incidents(component)]
sqlite.close()
print('PARIDAD REAL OK: save/upsert, get/ausente, duplicados/exclusión, activos y SELECT 1.')
