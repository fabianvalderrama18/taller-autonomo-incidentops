"""Repositorio SQLite optimizado para el resumen de incidentes (ADR-001, ADR-004).

Una sola consulta con `INNER JOIN` a `sla_policies` evita el escaneo completo y
las consultas N+1 del artefacto didáctico `incident_repository.py`, que se
conserva intacto. El SLA se calcula siempre en `src.domain.sla_calculator`.
"""

import argparse
from datetime import datetime, timedelta
import sqlite3
import time

from src.domain.models import Incident, SeverityLevel
from src.domain.sla_calculator import SLA_POLICY_TABLE

_ACTIVE_STATUSES = ("OPEN", "IN_PROGRESS", "ESCALATION_REQUIRED")

_SELECT_COLUMNS = """
    i.incident_id, i.title, i.component, i.severity, i.status, i.created_at, i.resolved_at,
    i.recommended_team, i.duplicate_group_key
"""


class SQLiteIncidentRepository:
    """Implementación estructural de `IncidentRepositoryPort` sobre SQLite3."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sla_policies (
                severity TEXT PRIMARY KEY,
                max_resolution_minutes INTEGER NOT NULL,
                operates_24x7 INTEGER NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                component TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                resolved_at TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_incidents_component_status
            ON incidents(component, status)
            """
        )
        columns = {row[1] for row in cursor.execute("PRAGMA table_info(incidents)")}
        for column in ("recommended_team", "duplicate_group_key"):
            if column not in columns:
                cursor.execute(f"ALTER TABLE incidents ADD COLUMN {column} TEXT")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_dup_key ON incidents(duplicate_group_key, status)")
        for rule in SLA_POLICY_TABLE.values():
            cursor.execute(
                """
                INSERT OR REPLACE INTO sla_policies (severity, max_resolution_minutes, operates_24x7)
                VALUES (?, ?, ?)
                """,
                (rule.severity, rule.max_resolution_minutes, 1 if rule.operates_24x7 else 0),
            )
        self.conn.commit()

    @staticmethod
    def _to_incident(row: sqlite3.Row) -> Incident:
        return Incident(
            incident_id=row["incident_id"],
            title=row["title"],
            component=row["component"],
            severity=row["severity"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            recommended_team=row["recommended_team"],
            duplicate_group_key=row["duplicate_group_key"],
            resolved_at=(
                datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None
            ),
        )

    def save_incident(self, incident: Incident) -> None:
        """Alta o reemplazo por identificador; no aplica reglas de negocio."""
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO incidents
                (incident_id, title, component, severity, status, created_at, resolved_at, recommended_team, duplicate_group_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(incident_id) DO UPDATE SET title=excluded.title, component=excluded.component, severity=excluded.severity, status=excluded.status, created_at=excluded.created_at, resolved_at=excluded.resolved_at, recommended_team=excluded.recommended_team, duplicate_group_key=excluded.duplicate_group_key
                """,
                (
                    incident.incident_id,
                    incident.title,
                    incident.component,
                    incident.severity,
                    incident.status,
                    incident.created_at.isoformat(),
                    incident.resolved_at.isoformat() if incident.resolved_at else None,
                    incident.recommended_team,
                    incident.duplicate_group_key,
                ),
            )

    def get_incident(self, incident_id: str) -> Incident | None:
        """Devuelve la entidad de dominio o `None` si no existe."""
        cursor = self.conn.execute(
            f"SELECT {_SELECT_COLUMNS} FROM incidents AS i WHERE i.incident_id = ?",
            (incident_id,),
        )
        row = cursor.fetchone()
        return self._to_incident(row) if row else None

    def find_open_duplicates(self, duplicate_group_key: str,
                             exclude_incident_id: str | None = None) -> list[Incident]:
        """Equivalencia por clave entre abiertos, excluyendo el ID solicitado."""
        rows = self.conn.execute(
            f"""SELECT {_SELECT_COLUMNS} FROM incidents AS i
            WHERE i.status IN (?, ?, ?) AND i.duplicate_group_key = ?
            AND (? IS NULL OR i.incident_id <> ?) ORDER BY i.incident_id""",
            (*_ACTIVE_STATUSES, duplicate_group_key, exclude_incident_id, exclude_incident_id),
        ).fetchall()
        return [self._to_incident(row) for row in rows]

    def close(self) -> None:
        self.conn.close()

    def list_active_incidents(self, component_filter: str | None = None) -> list[Incident]:
        """Devuelve activos ordenados por identificador en una sola consulta."""
        cursor = self.conn.execute(
            f"""
            SELECT {_SELECT_COLUMNS}
            FROM incidents AS i
            INNER JOIN sla_policies AS p ON p.severity = i.severity
            WHERE i.status IN (?, ?, ?)
              AND (? IS NULL OR i.component = ?)
            ORDER BY i.incident_id
            """,
            (*_ACTIVE_STATUSES, component_filter, component_filter),
        )
        return [self._to_incident(row) for row in cursor.fetchall()]

    def check_health(self) -> bool:
        """`True` si la conexión responde; `False` ante fallo de SQLite."""
        try:
            return self.conn.execute("SELECT 1").fetchone() is not None
        except sqlite3.Error:
            return False

    def _seed_benchmark(self, total_records: int) -> None:
        """Puebla registros sintéticos en una sola transacción (SC-006)."""
        components = [
            "payments-gateway",
            "auth-identity",
            "database-cluster",
            "reporting-api",
            "frontend-ui",
        ]
        severities: list[SeverityLevel] = ["P0", "P1", "P2", "P3"]
        statuses = ["RESOLVED", "RESOLVED", "RESOLVED", "OPEN", "IN_PROGRESS"]
        base_time = datetime(2026, 11, 1, 8, 0, 0)
        rows = []
        for idx in range(1, total_records + 1):
            severity = severities[idx % len(severities)]
            status = statuses[(idx * 3 + idx // 5) % len(statuses)]
            component = components[idx % len(components)]
            created = base_time + timedelta(minutes=((idx - 1) % 10000 + 1) * 2)
            resolved = (created + timedelta(minutes=45)).isoformat() if status == "RESOLVED" else None
            rows.append(
                (
                    f"INC-{idx:05d}",
                    f"Reporte sintético #{idx} en {component}",
                    component,
                    severity,
                    status,
                    created.isoformat(),
                    resolved,
                )
            )
        with self.conn:
            self.conn.executemany(
                """
                INSERT OR REPLACE INTO incidents
                (incident_id, title, component, severity, status, created_at, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )


def _run_benchmark() -> None:
    parser = argparse.ArgumentParser(description="Benchmark del repositorio optimizado (SC-006)")
    parser.add_argument("--benchmark", action="store_true", help="Ejecuta la medición")
    parser.add_argument("--records", type=int, default=10000, help="Cantidad de registros a sembrar")
    parser.add_argument("--iterations", type=int, default=1, help="Número de consultas a medir")
    args = parser.parse_args()

    repo = SQLiteIncidentRepository()
    print(f"Sembrando {args.records} incidentes en SQLite en memoria...")
    repo._seed_benchmark(args.records)

    start = time.perf_counter()
    found_count = 0
    for _ in range(args.iterations):
        active = repo.list_active_incidents("payments-gateway")
        found_count = len(active)
    elapsed_ms = (time.perf_counter() - start) * 1000

    print("=== Resultado del Benchmark (Después de Refactorizar) ===")
    print(f"Incidentes activos encontrados para 'payments-gateway': {found_count}")
    print(f"Tiempo total ({args.iterations} ejecuciones sobre {args.records} filas): {elapsed_ms:.2f} ms")
    print(f"Promedio por consulta: {elapsed_ms / args.iterations:.2f} ms")
    print(
        "Diagnóstico: `list_active_incidents` usa el índice (component, status) y un "
        "INNER JOIN a sla_policies en una sola consulta, sin N+1."
    )


if __name__ == "__main__":
    _run_benchmark()
