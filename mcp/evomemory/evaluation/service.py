from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class EvaluationPlaneService:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else None
        self._metrics: dict[str, int] = {}
        if self.path is not None:
            self._initialize()

    def _connect(self) -> sqlite3.Connection:
        if self.path is None:
            raise RuntimeError(
                "EvaluationPlaneService is running without SQLite persistence"
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluation_metrics (
                    key TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback_records (
                    id TEXT PRIMARY KEY,
                    target_kind TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    delta INTEGER NOT NULL,
                    note TEXT,
                    created_at TEXT
                )
                """
            )

    def increment(self, key: str, amount: int = 1) -> None:
        if self.path is None:
            self._metrics[key] = self._metrics.get(key, 0) + amount
            return
        with self._connect() as connection:
            current = connection.execute(
                "SELECT value FROM evaluation_metrics WHERE key = ?",
                (key,),
            ).fetchone()
            value = int(current[0]) if current else 0
            connection.execute(
                "INSERT OR REPLACE INTO evaluation_metrics (key, value) VALUES (?, ?)",
                (key, value + amount),
            )

    def summary(self) -> dict:
        if self.path is None:
            metrics = dict(self._metrics)
        else:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT key, value FROM evaluation_metrics ORDER BY key"
                ).fetchall()
            metrics = {row[0]: int(row[1]) for row in rows}
        return {
            "plane": "evaluation",
            "metrics": metrics,
        }

    def record_feedback(
        self,
        *,
        target_kind: str,
        target_id: str,
        signal: str,
        delta: int,
        note: str | None = None,
    ) -> dict:
        record = {
            "id": None,
            "target_kind": target_kind,
            "target_id": target_id,
            "signal": signal,
            "delta": delta,
            "note": note,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.path is None:
            record["id"] = (
                f"feedback_{len(getattr(self, '_feedback_records', [])) + 1:04d}"
            )
            if not hasattr(self, "_feedback_records"):
                self._feedback_records = []
            self._feedback_records.append(record)
        else:
            with self._connect() as connection:
                current = connection.execute(
                    "SELECT COUNT(*) FROM feedback_records"
                ).fetchone()
                record["id"] = f"feedback_{int(current[0] or 0) + 1:04d}"
                connection.execute(
                    "INSERT INTO feedback_records (id, target_kind, target_id, signal, delta, note, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        record["id"],
                        record["target_kind"],
                        record["target_id"],
                        record["signal"],
                        record["delta"],
                        record["note"],
                        record["created_at"],
                    ),
                )
        self.increment("feedback_records")
        self.increment(f"feedback_{signal}")
        if delta > 0:
            self.increment("positive_feedback")
        elif delta < 0:
            self.increment("negative_feedback")
        return record

    def list_feedback(
        self,
        *,
        target_kind: str | None = None,
        target_id: str | None = None,
        limit: int = 20,
    ) -> dict:
        if self.path is None:
            records = list(getattr(self, "_feedback_records", []))
        else:
            query = "SELECT id, target_kind, target_id, signal, delta, note, created_at FROM feedback_records"
            params = []
            clauses = []
            if target_kind is not None:
                clauses.append("target_kind = ?")
                params.append(target_kind)
            if target_id is not None:
                clauses.append("target_id = ?")
                params.append(target_id)
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            query += " ORDER BY created_at DESC, id DESC"
            with self._connect() as connection:
                rows = connection.execute(query, tuple(params)).fetchall()
            records = [
                {
                    "id": row[0],
                    "target_kind": row[1],
                    "target_id": row[2],
                    "signal": row[3],
                    "delta": int(row[4]),
                    "note": row[5],
                    "created_at": row[6],
                }
                for row in rows
            ]
        if target_kind is not None and self.path is None:
            records = [
                item for item in records if item.get("target_kind") == target_kind
            ]
        if target_id is not None and self.path is None:
            records = [item for item in records if item.get("target_id") == target_id]
        records = sorted(
            records,
            key=lambda item: (item.get("created_at") or "", item.get("id") or ""),
            reverse=True,
        )
        return {
            "target_kind": target_kind,
            "target_id": target_id,
            "count": len(records[:limit]),
            "records": records[:limit],
        }


__all__ = ["EvaluationPlaneService"]
