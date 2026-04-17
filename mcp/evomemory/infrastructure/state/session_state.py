from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class SessionStateStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._migrate_legacy_json_if_needed()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS session_state (
                    session_id TEXT PRIMARY KEY,
                    directory TEXT,
                    wing TEXT,
                    last_saved_message_id TEXT,
                    last_saved_signature TEXT,
                    last_saved_order INTEGER,
                    last_saved_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_state (
                    key TEXT PRIMARY KEY,
                    value_json TEXT
                )
                """
            )

    def _migrate_legacy_json_if_needed(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return

        sessions = payload.get("sessions")
        if not isinstance(sessions, dict):
            return

        backup_path = self.path.with_suffix(self.path.suffix + ".bak")
        self.path.replace(backup_path)
        self._initialize()
        self.save({"sessions": sessions})

    def load(self) -> dict[str, Any]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    session_id,
                    directory,
                    wing,
                    last_saved_message_id,
                    last_saved_signature,
                    last_saved_order,
                    last_saved_at
                FROM session_state
                ORDER BY session_id
                """
            ).fetchall()
            runtime_rows = connection.execute(
                "SELECT key, value_json FROM runtime_state ORDER BY key"
            ).fetchall()

        sessions = {}
        for row in rows:
            (
                session_id,
                directory,
                wing,
                last_saved_message_id,
                last_saved_signature,
                last_saved_order,
                last_saved_at,
            ) = row
            sessions[session_id] = {
                "directory": directory,
                "wing": wing,
                "last_saved_message_id": last_saved_message_id,
                "last_saved_signature": last_saved_signature,
                "last_saved_order": int(last_saved_order or 0),
                "last_saved_at": last_saved_at,
            }
        runtime = {}
        for key, value_json in runtime_rows:
            runtime[key] = json.loads(value_json)
        return {"sessions": sessions, "runtime": runtime}

    def save(self, state: dict[str, Any]) -> None:
        sessions = state.get("sessions", {})
        runtime = state.get("runtime", {})
        with self._connect() as connection:
            connection.execute("DELETE FROM session_state")
            connection.execute("DELETE FROM runtime_state")
            connection.executemany(
                """
                INSERT INTO session_state (
                    session_id,
                    directory,
                    wing,
                    last_saved_message_id,
                    last_saved_signature,
                    last_saved_order,
                    last_saved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        session_id,
                        payload.get("directory"),
                        payload.get("wing"),
                        payload.get("last_saved_message_id"),
                        payload.get("last_saved_signature"),
                        int(payload.get("last_saved_order") or 0),
                        payload.get("last_saved_at"),
                    )
                    for session_id, payload in sessions.items()
                ],
            )
            connection.executemany(
                "INSERT INTO runtime_state (key, value_json) VALUES (?, ?)",
                [(key, json.dumps(value)) for key, value in runtime.items()],
            )

    def summary(self) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*), MAX(last_saved_at) FROM session_state"
            ).fetchone()

        session_count, last_saved_at = row or (0, None)
        return {
            "state_backend": "sqlite",
            "session_count": int(session_count or 0),
            "last_saved_at": last_saved_at,
        }


__all__ = ["SessionStateStore"]
