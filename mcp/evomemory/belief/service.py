from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class BeliefPlaneService:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else None
        self._facts: list[dict[str, Any]] = []
        if self.path is not None:
            self._initialize()

    def _connect(self) -> sqlite3.Connection:
        if self.path is None:
            raise RuntimeError(
                "BeliefPlaneService is running without SQLite persistence"
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS belief_facts (
                    id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    memory_tier TEXT NOT NULL,
                    source_session TEXT,
                    source_message_id TEXT,
                    source_record_id TEXT,
                    source_count INTEGER NOT NULL DEFAULT 1,
                    last_confirmed_at TEXT,
                    valid_from TEXT,
                    valid_to TEXT,
                    superseded_by TEXT,
                    confidence REAL
                )
                """
            )
            self._ensure_column(
                connection,
                "belief_facts",
                "source_count",
                "INTEGER NOT NULL DEFAULT 1",
            )
            self._ensure_column(
                connection,
                "belief_facts",
                "last_confirmed_at",
                "TEXT",
            )

    def _ensure_column(
        self, connection: sqlite3.Connection, table: str, column: str, declaration: str
    ) -> None:
        columns = {
            row[1]
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column in columns:
            return
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")

    def _confidence_for_source_count(self, source_count: int) -> float:
        return min(1.0, 0.4 + 0.2 * max(1, source_count))

    def _fetch_by_id(self, belief_id: str) -> dict[str, Any] | None:
        return next(
            (item for item in self._fetch_rows() if item.get("id") == belief_id), None
        )

    def _fetch_rows(self) -> list[dict[str, Any]]:
        if self.path is None:
            return list(self._facts)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, scope, key, value, memory_tier, source_session,
                       source_message_id, source_record_id, source_count,
                       last_confirmed_at, valid_from, valid_to,
                       superseded_by, confidence
                FROM belief_facts
                ORDER BY valid_from DESC, id DESC
                """
            ).fetchall()
        return [
            {
                "id": row[0],
                "scope": row[1],
                "key": row[2],
                "value": row[3],
                "memory_tier": row[4],
                "source_session": row[5],
                "source_message_id": row[6],
                "source_record_id": row[7],
                "source_count": int(row[8] or 1),
                "last_confirmed_at": row[9] or row[10],
                "valid_from": row[10],
                "valid_to": row[11],
                "superseded_by": row[12],
                "confidence": row[13],
                "plane": "belief",
                "kind": "preference" if row[4] == "user_preference" else "fact",
                "is_stale": row[11] is not None,
            }
            for row in rows
        ]

    def status(self) -> dict[str, Any]:
        rows = self._fetch_rows()
        current_count = len([item for item in rows if not item.get("valid_to")])
        return {
            "plane": "belief",
            "fact_count": len(rows),
            "current_fact_count": current_count,
            "historical_fact_count": len(rows) - current_count,
        }

    def promote(
        self,
        *,
        scope: str,
        key: str,
        value: str,
        memory_tier: str,
        source_session: str,
        source_message_id: str | None,
        source_record_id: str | None,
        valid_from: str | None = None,
        initial_source_count: int = 1,
    ) -> dict[str, Any]:
        timestamp = valid_from or datetime.now(timezone.utc).isoformat()
        current_facts = [
            item
            for item in self._fetch_rows()
            if item.get("scope") == scope
            and item.get("key") == key
            and not item.get("valid_to")
        ]
        for item in current_facts:
            if item.get("value") == value:
                updated_fact = {
                    **item,
                    "source_session": source_session,
                    "source_message_id": source_message_id,
                    "source_record_id": source_record_id,
                    "source_count": int(item.get("source_count") or 1) + 1,
                    "last_confirmed_at": timestamp,
                }
                updated_fact["confidence"] = self._confidence_for_source_count(
                    updated_fact["source_count"]
                )
                if self.path is None:
                    for existing in self._facts:
                        if existing.get("id") == item["id"]:
                            existing.update(updated_fact)
                            break
                else:
                    with self._connect() as connection:
                        connection.execute(
                            """
                            UPDATE belief_facts
                            SET source_session = ?,
                                source_message_id = ?,
                                source_record_id = ?,
                                source_count = ?,
                                last_confirmed_at = ?,
                                confidence = ?
                            WHERE id = ?
                            """,
                            (
                                updated_fact["source_session"],
                                updated_fact["source_message_id"],
                                updated_fact["source_record_id"],
                                updated_fact["source_count"],
                                updated_fact["last_confirmed_at"],
                                updated_fact["confidence"],
                                updated_fact["id"],
                            ),
                        )
                return {"created": False, "fact": updated_fact, "superseded": []}

        fact_id = f"belief_{hashlib.sha1(f'{scope}:{key}:{value}:{timestamp}'.encode('utf-8')).hexdigest()[:16]}"
        superseded = []
        for item in current_facts:
            item["valid_to"] = timestamp
            item["superseded_by"] = fact_id
            superseded.append(item)

        fact = {
            "id": fact_id,
            "scope": scope,
            "plane": "belief",
            "kind": "preference" if memory_tier == "user_preference" else "fact",
            "key": key,
            "value": value,
            "memory_tier": memory_tier,
            "source_session": source_session,
            "source_message_id": source_message_id,
            "source_record_id": source_record_id,
            "source_count": max(1, int(initial_source_count or 1)),
            "last_confirmed_at": timestamp,
            "valid_from": timestamp,
            "valid_to": None,
            "superseded_by": None,
            "confidence": self._confidence_for_source_count(
                max(1, int(initial_source_count or 1))
            ),
        }
        if self.path is None:
            for item in current_facts:
                for existing in self._facts:
                    if existing.get("id") == item["id"]:
                        existing["valid_to"] = timestamp
                        existing["superseded_by"] = fact_id
            self._facts.append(fact)
        else:
            with self._connect() as connection:
                for item in current_facts:
                    connection.execute(
                        "UPDATE belief_facts SET valid_to = ?, superseded_by = ? WHERE id = ?",
                        (timestamp, fact_id, item["id"]),
                    )
                connection.execute(
                    """
                    INSERT INTO belief_facts (
                        id, scope, key, value, memory_tier, source_session,
                        source_message_id, source_record_id, source_count,
                        last_confirmed_at, valid_from, valid_to,
                        superseded_by, confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fact["id"],
                        fact["scope"],
                        fact["key"],
                        fact["value"],
                        fact["memory_tier"],
                        fact["source_session"],
                        fact["source_message_id"],
                        fact["source_record_id"],
                        fact["source_count"],
                        fact["last_confirmed_at"],
                        fact["valid_from"],
                        fact["valid_to"],
                        fact["superseded_by"],
                        fact["confidence"],
                    ),
                )
        return {"created": True, "fact": fact, "superseded": superseded}

    def query(
        self,
        *,
        scope: str | None = None,
        key: str | None = None,
        current_only: bool = False,
        historical_only: bool = False,
        min_confidence: float | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        rows = self._fetch_rows()
        if scope is not None:
            rows = [item for item in rows if item.get("scope") == scope]
        if key is not None:
            rows = [item for item in rows if item.get("key") == key]
        if current_only:
            rows = [item for item in rows if not item.get("valid_to")]
        elif historical_only:
            rows = [item for item in rows if item.get("valid_to")]
        if min_confidence is not None:
            rows = [
                item
                for item in rows
                if float(item.get("confidence") or 0) >= float(min_confidence)
            ]
        rows = sorted(
            rows,
            key=lambda item: (
                item.get("valid_from") or "",
                item.get("id") or "",
            ),
            reverse=True,
        )
        return {
            "scope": scope,
            "key": key,
            "current_only": current_only,
            "historical_only": historical_only,
            "min_confidence": min_confidence,
            "count": len(rows[:limit]),
            "facts": rows[:limit],
        }

    def stale_source_records(self) -> list[dict[str, Any]]:
        rows = [item for item in self._fetch_rows() if item.get("valid_to")]
        rows = sorted(
            rows,
            key=lambda item: (
                item.get("valid_to") or "",
                item.get("id") or "",
            ),
            reverse=True,
        )
        return [
            {
                "belief_id": item.get("id"),
                "source_record_id": item.get("source_record_id"),
                "source_session": item.get("source_session"),
                "source_message_id": item.get("source_message_id"),
                "memory_tier": item.get("memory_tier"),
                "key": item.get("key"),
                "value": item.get("value"),
                "valid_to": item.get("valid_to"),
            }
            for item in rows
        ]

    def apply_feedback(
        self,
        *,
        target_id: str,
        signal: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        target = self._fetch_by_id(target_id)
        if target is None:
            raise KeyError(f"Unknown belief: {target_id}")

        delta_map = {
            "success": 2,
            "confirm": 1,
            "reject": -1,
            "correct": -2,
        }
        delta = delta_map.get(signal, 0)
        timestamp = datetime.now(timezone.utc).isoformat()
        updated = {**target}

        if delta > 0:
            updated["source_count"] = int(target.get("source_count") or 1) + 1
            updated["last_confirmed_at"] = timestamp
            updated["confidence"] = self._confidence_for_source_count(
                updated["source_count"]
            )
        elif delta < 0:
            updated["last_confirmed_at"] = timestamp
            updated["confidence"] = max(
                0.0, float(target.get("confidence") or 0) + (delta * 0.1)
            )

        if self.path is None:
            for index, item in enumerate(self._facts):
                if item.get("id") == target_id:
                    self._facts[index] = updated
                    break
        else:
            with self._connect() as connection:
                connection.execute(
                    """
                    UPDATE belief_facts
                    SET source_count = ?,
                        last_confirmed_at = ?,
                        confidence = ?
                    WHERE id = ?
                    """,
                    (
                        updated.get("source_count") or 1,
                        updated.get("last_confirmed_at"),
                        updated.get("confidence"),
                        target_id,
                    ),
                )

        return {**updated, "delta": delta, "note": note, "signal": signal}

    def run_revision(self, *, min_confidence: float) -> dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        current_facts = [
            item
            for item in self._fetch_rows()
            if not item.get("valid_to")
            and float(item.get("confidence") or 0) < float(min_confidence)
        ]
        revised = []
        if self.path is None:
            for fact in current_facts:
                for existing in self._facts:
                    if existing.get("id") != fact["id"]:
                        continue
                    existing["valid_to"] = timestamp
                    existing["is_stale"] = True
                    revised.append({**existing})
                    break
        else:
            with self._connect() as connection:
                for fact in current_facts:
                    connection.execute(
                        "UPDATE belief_facts SET valid_to = ? WHERE id = ?",
                        (timestamp, fact["id"]),
                    )
            revised = [
                item
                for item in self._fetch_rows()
                if item.get("id") in {fact["id"] for fact in current_facts}
            ]
        return {
            "threshold": float(min_confidence),
            "revised_count": len(revised),
            "revised_beliefs": revised,
        }


__all__ = ["BeliefPlaneService"]
