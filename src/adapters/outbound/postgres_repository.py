"""Adaptador PostgreSQL sin ORM; conexiones acotadas por operación (ADR-006)."""

from dataclasses import asdict
from datetime import datetime

import psycopg
from psycopg.rows import dict_row

from src.domain.models import Incident

_COLUMNS = "incident_id, title, component, severity, status, created_at, resolved_at, recommended_team, duplicate_group_key"


class PostgresIncidentRepository:
    """Conexión diferida: construir el adaptador no oculta una caída de la BD."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _connect(self):
        return psycopg.connect(
            self.database_url, row_factory=dict_row, connect_timeout=3
        )

    @staticmethod
    def _schema(conn) -> None:
        conn.execute("""CREATE TABLE IF NOT EXISTS incidents (
            incident_id TEXT PRIMARY KEY, title TEXT NOT NULL, component TEXT NOT NULL,
            severity TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
            resolved_at TEXT, recommended_team TEXT, duplicate_group_key TEXT)""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_incidents_dup_key ON incidents(duplicate_group_key, status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_incidents_component_status ON incidents(component, status)"
        )

    @staticmethod
    def _entity(row) -> Incident:
        values = dict(row)
        values["created_at"] = datetime.fromisoformat(values["created_at"])
        values["resolved_at"] = (
            datetime.fromisoformat(values["resolved_at"])
            if values["resolved_at"]
            else None
        )
        return Incident(**values)

    def save_incident(self, incident: Incident) -> None:
        values = asdict(incident)
        values["created_at"] = incident.created_at.isoformat()
        values["resolved_at"] = (
            incident.resolved_at.isoformat() if incident.resolved_at else None
        )
        with self._connect() as conn:
            self._schema(conn)
            conn.execute(
                f"""INSERT INTO incidents ({_COLUMNS})
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (incident_id) DO UPDATE SET title=excluded.title,
                component=excluded.component, severity=excluded.severity, status=excluded.status,
                created_at=excluded.created_at, resolved_at=excluded.resolved_at,
                recommended_team=excluded.recommended_team, duplicate_group_key=excluded.duplicate_group_key""",
                tuple(values[column] for column in _COLUMNS.split(", ")),
            )

    def _read(self, condition: str, parameters: tuple) -> list[Incident]:
        with self._connect() as conn:
            self._schema(conn)
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM incidents WHERE {condition} ORDER BY incident_id",
                parameters,
            ).fetchall()
        return [self._entity(row) for row in rows]

    def get_incident(self, incident_id: str) -> Incident | None:
        rows = self._read("incident_id = %s", (incident_id,))
        return rows[0] if rows else None

    def find_open_duplicates(
        self, duplicate_group_key: str, exclude_incident_id: str | None = None
    ) -> list[Incident]:
        condition = "status IN ('OPEN','IN_PROGRESS','ESCALATION_REQUIRED') AND duplicate_group_key = %s"
        params = (duplicate_group_key,)
        if exclude_incident_id is not None:
            condition += " AND incident_id <> %s"
            params += (exclude_incident_id,)
        return self._read(condition, params)

    def list_active_incidents(
        self, component_filter: str | None = None
    ) -> list[Incident]:
        condition = "status IN ('OPEN','IN_PROGRESS','ESCALATION_REQUIRED')"
        params = ()
        if component_filter is not None:
            condition += " AND component = %s"
            params = (component_filter,)
        return self._read(condition, params)

    def check_health(self) -> bool:
        try:
            with self._connect() as conn:
                return conn.execute("SELECT 1 AS healthy").fetchone()["healthy"] == 1
        except psycopg.Error:
            return False
