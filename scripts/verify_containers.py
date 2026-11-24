"""Prueba real de API/CLI PostgreSQL, reinicio y pérdida de conectividad.

Ejecutar después de docker compose -p incidentops-taller up --build -d.
Solo opera sobre el proyecto Compose indicado; conserva el volumen.
"""
import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
from uuid import uuid4

parser = argparse.ArgumentParser()
parser.add_argument('--project', default='incidentops-taller')
args = parser.parse_args()
compose = ['docker', 'compose', '-p', args.project]


def command(*parts):
    result = subprocess.run([*compose, *parts], text=True, capture_output=True, check=True)
    return result.stdout.strip()


def request(path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request('http://localhost:8000' + path, data=data,
                                 headers={'Content-Type': 'application/json'})
    try:
        response = urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as error:
        response = error
    return response.status, json.load(response)


def wait_health(expected):
    for _ in range(30):
        try:
            status, body = request('/health')
            if status == expected:
                print(f'GET /health -> {status} {body}', flush=True)
                return
        except (OSError, ValueError):
            pass
        time.sleep(1)
    raise AssertionError(f'Salud no alcanzó {expected}')


wait_health(200)
identifier = 'VERIFY-' + uuid4().hex[:8]
body = dict(incident_id=identifier, title='Cuenta bloqueada',
            raw_text='Mi cuenta individual está bloqueada hoy y no puedo acceder',
            created_at='2026-11-06T17:00:00')
status, created = request('/api/v1/incidents', body)
assert status == 201 and created['severity'] == 'P2', (status, created)
print('POST incidente -> 201, clasificación P2 persistida', flush=True)
status, duplicate = request('/api/v1/incidents', {**body, 'incident_id': identifier + '-DUP'})
assert status == 201 and identifier in duplicate['duplicate_of']
print('POST equivalente -> 201, duplicado abierto detectado', flush=True)
path = f'/api/v1/incidents/{identifier}/sla?reference_time=2026-11-09T09:00:00'
status, evaluation = request(path)
assert status == 200 and evaluation['elapsed_minutes'] == 120 and evaluation['remaining_minutes'] == 360
cli = json.loads(command('exec', '-T', 'api', 'python', '-m', 'src.adapters.inbound.cli',
                         'sla', '--incident-id', identifier, '--reference-time', '2026-11-09T09:00:00'))
assert cli == evaluation
print('SLA HTTP = CLI: 120 usados / 480 permitidos / 360 restantes', flush=True)
assert json.loads(command('exec', '-T', 'api', 'python', '-m', 'src.adapters.inbound.cli',
                          'health')) == {'status': 'ok', 'database': 'connected'}
command('restart', 'api', 'db')
wait_health(200)
assert request(path) == (200, evaluation)
print('Reinicio api + db: incidente y SLA conservados en volumen', flush=True)
try:
    command('stop', 'db')
    wait_health(503)
finally:
    command('start', 'db')
wait_health(200)
print('Recuperación de PostgreSQL verificada', flush=True)
print(command('ps'), flush=True)
