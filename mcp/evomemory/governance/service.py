from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import sqlite3
from pathlib import Path


class GovernancePlaneService:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else None
        self._genes: list[dict] = []
        self._capsules: list[dict] = []
        self._events: list[dict] = []
        if self.path is not None:
            self._initialize()

    def _connect(self) -> sqlite3.Connection:
        if self.path is None:
            raise RuntimeError(
                "GovernancePlaneService is running without SQLite persistence"
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS genes (
                    id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    source_fact_id TEXT,
                    created_at TEXT,
                    score INTEGER NOT NULL DEFAULT 0,
                    is_stale INTEGER NOT NULL DEFAULT 0,
                    demoted_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS capsules (
                    id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    gene_ids_json TEXT NOT NULL,
                    updated_at TEXT,
                    score INTEGER NOT NULL DEFAULT 0,
                    is_stale INTEGER NOT NULL DEFAULT 0,
                    demoted_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS evolution_events (
                    id TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    target_kind TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    rationale TEXT,
                    source_record_id TEXT,
                    created_at TEXT
                )
                """
            )
            self._ensure_column(
                connection, "genes", "score", "INTEGER NOT NULL DEFAULT 0"
            )
            self._ensure_column(
                connection, "genes", "is_stale", "INTEGER NOT NULL DEFAULT 0"
            )
            self._ensure_column(connection, "genes", "demoted_at", "TEXT")
            self._ensure_column(
                connection, "capsules", "score", "INTEGER NOT NULL DEFAULT 0"
            )
            self._ensure_column(
                connection, "capsules", "is_stale", "INTEGER NOT NULL DEFAULT 0"
            )
            self._ensure_column(connection, "capsules", "demoted_at", "TEXT")

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

    def _fetch_events(self) -> list[dict]:
        if self.path is None:
            return list(self._events)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, action, target_kind, target_id, rationale, source_record_id, created_at FROM evolution_events ORDER BY created_at DESC, id DESC"
            ).fetchall()
        return [
            {
                "id": row[0],
                "action": row[1],
                "target_kind": row[2],
                "target_id": row[3],
                "rationale": row[4],
                "source_record_id": row[5],
                "created_at": row[6],
            }
            for row in rows
        ]

    def _fetch_genes(self) -> list[dict]:
        if self.path is None:
            return list(self._genes)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, scope, key, value, summary, source_fact_id, created_at, score, is_stale, demoted_at FROM genes ORDER BY created_at DESC, id DESC"
            ).fetchall()
        return [
            {
                "id": row[0],
                "scope": row[1],
                "key": row[2],
                "value": row[3],
                "summary": row[4],
                "source_fact_id": row[5],
                "created_at": row[6],
                "score": int(row[7] or 0),
                "is_stale": bool(row[8]),
                "demoted_at": row[9],
            }
            for row in rows
        ]

    def _fetch_capsules(self) -> list[dict]:
        if self.path is None:
            return list(self._capsules)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, scope, summary, gene_ids_json, updated_at, score, is_stale, demoted_at FROM capsules ORDER BY updated_at DESC, id DESC"
            ).fetchall()
        return [
            {
                "id": row[0],
                "scope": row[1],
                "summary": row[2],
                "gene_ids": json.loads(row[3] or "[]"),
                "updated_at": row[4],
                "score": int(row[5] or 0),
                "is_stale": bool(row[6]),
                "demoted_at": row[7],
            }
            for row in rows
        ]

    def status(self) -> dict:
        return {
            "plane": "governance",
            "gene_count": len(self._fetch_genes()),
            "capsule_count": len(self._fetch_capsules()),
            "event_count": len(self._fetch_events()),
            "stale_gene_count": len(
                [item for item in self._fetch_genes() if item.get("is_stale")]
            ),
            "stale_capsule_count": len(
                [item for item in self._fetch_capsules() if item.get("is_stale")]
            ),
        }

    def list_genes(
        self,
        *,
        scope: str | None = None,
        key: str | None = None,
        current_only: bool = False,
        stale_only: bool = False,
        limit: int = 10,
    ) -> dict:
        genes = self._fetch_genes()
        if scope is not None:
            genes = [item for item in genes if item.get("scope") == scope]
        if key is not None:
            genes = [item for item in genes if item.get("key") == key]
        if current_only:
            genes = [item for item in genes if not item.get("is_stale")]
        elif stale_only:
            genes = [item for item in genes if item.get("is_stale")]
        return {"count": len(genes[:limit]), "genes": genes[:limit]}

    def list_capsules(
        self,
        *,
        scope: str | None = None,
        current_only: bool = False,
        stale_only: bool = False,
        limit: int = 10,
    ) -> dict:
        capsules = self._fetch_capsules()
        if scope is not None:
            capsules = [item for item in capsules if item.get("scope") == scope]
        if current_only:
            capsules = [item for item in capsules if not item.get("is_stale")]
        elif stale_only:
            capsules = [item for item in capsules if item.get("is_stale")]
        return {"count": len(capsules[:limit]), "capsules": capsules[:limit]}

    def ensure_gene_from_belief(self, fact: dict) -> dict:
        key = fact.get("key") or "unknown"
        value = fact.get("value") or "unknown"
        scope = fact.get("scope") or "project"
        gene_id = f"gene_{hashlib.sha1(f'{scope}:{key}:{value}'.encode('utf-8')).hexdigest()[:16]}"
        existing = next(
            (item for item in self._fetch_genes() if item.get("id") == gene_id), None
        )
        if existing is not None:
            return {"created": False, "gene": existing}
        gene = {
            "id": gene_id,
            "scope": scope,
            "key": key,
            "value": value,
            "summary": f"Respect {scope} belief {key}={value}",
            "source_fact_id": fact.get("id"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "score": 0,
            "is_stale": False,
            "demoted_at": None,
        }
        if self.path is None:
            self._genes.append(gene)
        else:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO genes (id, scope, key, value, summary, source_fact_id, created_at, score, is_stale, demoted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        gene["id"],
                        gene["scope"],
                        gene["key"],
                        gene["value"],
                        gene["summary"],
                        gene["source_fact_id"],
                        gene["created_at"],
                        gene["score"],
                        int(gene["is_stale"]),
                        gene["demoted_at"],
                    ),
                )
        return {"created": True, "gene": gene}

    def ensure_capsule_for_gene(self, scope: str, gene_id: str) -> dict:
        capsule_id = f"capsule_{scope}"
        existing = next(
            (item for item in self._fetch_capsules() if item.get("id") == capsule_id),
            None,
        )
        updated_at = datetime.now(timezone.utc).isoformat()
        if existing is None:
            capsule = {
                "id": capsule_id,
                "scope": scope,
                "summary": f"Reusable {scope} governance capsule",
                "gene_ids": [gene_id],
                "updated_at": updated_at,
                "score": 0,
                "is_stale": False,
                "demoted_at": None,
            }
            if self.path is None:
                self._capsules.append(capsule)
            else:
                with self._connect() as connection:
                    connection.execute(
                        "INSERT INTO capsules (id, scope, summary, gene_ids_json, updated_at, score, is_stale, demoted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            capsule["id"],
                            capsule["scope"],
                            capsule["summary"],
                            json.dumps(capsule["gene_ids"]),
                            capsule["updated_at"],
                            capsule["score"],
                            int(capsule["is_stale"]),
                            capsule["demoted_at"],
                        ),
                    )
            return {"created": True, "capsule": capsule}

        if gene_id in existing.get("gene_ids", []):
            return {"created": False, "capsule": existing}

        updated_gene_ids = [*existing.get("gene_ids", []), gene_id]
        capsule = {
            **existing,
            "gene_ids": updated_gene_ids,
            "updated_at": updated_at,
            "is_stale": False,
        }
        if self.path is None:
            for index, item in enumerate(self._capsules):
                if item.get("id") == capsule_id:
                    self._capsules[index] = capsule
                    break
        else:
            with self._connect() as connection:
                connection.execute(
                    "UPDATE capsules SET gene_ids_json = ?, updated_at = ?, is_stale = 0 WHERE id = ?",
                    (json.dumps(updated_gene_ids), updated_at, capsule_id),
                )
        return {"created": False, "capsule": capsule}

    def touch_assets(self, *, gene_ids: list[str], capsule_ids: list[str]) -> dict:
        gene_updates = 0
        capsule_updates = 0
        if self.path is None:
            for gene in self._genes:
                if gene.get("id") in set(gene_ids):
                    gene["score"] = int(gene.get("score") or 0) + 1
                    gene["is_stale"] = False
                    gene_updates += 1
            for capsule in self._capsules:
                if capsule.get("id") in set(capsule_ids):
                    capsule["score"] = int(capsule.get("score") or 0) + 1
                    capsule["is_stale"] = False
                    capsule_updates += 1
            return {"gene_updates": gene_updates, "capsule_updates": capsule_updates}

        with self._connect() as connection:
            for gene_id in gene_ids:
                result = connection.execute(
                    "UPDATE genes SET score = score + 1, is_stale = 0 WHERE id = ?",
                    (gene_id,),
                )
                gene_updates += int(result.rowcount or 0)
            for capsule_id in capsule_ids:
                result = connection.execute(
                    "UPDATE capsules SET score = score + 1, is_stale = 0 WHERE id = ?",
                    (capsule_id,),
                )
                capsule_updates += int(result.rowcount or 0)
        return {"gene_updates": gene_updates, "capsule_updates": capsule_updates}

    def demote_assets_for_superseded_beliefs(self, belief_ids: list[str]) -> dict:
        if not belief_ids:
            return {"genes": [], "capsules": []}
        belief_id_set = set(belief_ids)
        genes = [
            item
            for item in self._fetch_genes()
            if item.get("source_fact_id") in belief_id_set
        ]
        demoted_at = datetime.now(timezone.utc).isoformat()
        demoted_genes = []
        demoted_capsules = []

        if self.path is None:
            for gene in self._genes:
                if gene.get("source_fact_id") not in belief_id_set:
                    continue
                gene["score"] = max(0, int(gene.get("score") or 0) - 1)
                gene["is_stale"] = True
                gene["demoted_at"] = demoted_at
                demoted_genes.append(gene)
            demoted_gene_ids = {item["id"] for item in demoted_genes}
            for capsule in self._capsules:
                if not demoted_gene_ids.intersection(set(capsule.get("gene_ids", []))):
                    continue
                capsule["score"] = max(0, int(capsule.get("score") or 0) - 1)
                if set(capsule.get("gene_ids", [])).issubset(demoted_gene_ids):
                    capsule["is_stale"] = True
                capsule["demoted_at"] = demoted_at
                demoted_capsules.append(capsule)
            return {"genes": demoted_genes, "capsules": demoted_capsules}

        with self._connect() as connection:
            demoted_gene_ids = set()
            for gene in genes:
                connection.execute(
                    "UPDATE genes SET score = CASE WHEN score > 0 THEN score - 1 ELSE 0 END, is_stale = 1, demoted_at = ? WHERE id = ?",
                    (demoted_at, gene["id"]),
                )
                demoted_gene_ids.add(gene["id"])
            capsules = self._fetch_capsules()
            for capsule in capsules:
                capsule_gene_ids = set(capsule.get("gene_ids", []))
                if not demoted_gene_ids.intersection(capsule_gene_ids):
                    continue
                is_stale = int(capsule_gene_ids.issubset(demoted_gene_ids))
                connection.execute(
                    "UPDATE capsules SET score = CASE WHEN score > 0 THEN score - 1 ELSE 0 END, is_stale = ?, demoted_at = ? WHERE id = ?",
                    (is_stale, demoted_at, capsule["id"]),
                )
            demoted_genes = [
                item
                for item in self._fetch_genes()
                if item.get("id") in demoted_gene_ids
            ]
            demoted_capsules = [
                item
                for item in self._fetch_capsules()
                if demoted_gene_ids.intersection(set(item.get("gene_ids", [])))
            ]
        return {"genes": demoted_genes, "capsules": demoted_capsules}

    def demote_assets_for_revised_beliefs(self, belief_ids: list[str]) -> dict:
        return self.demote_assets_for_superseded_beliefs(belief_ids)

    def reconcile_stale_assets(self, stale_belief_ids: list[str]) -> dict:
        stale_belief_id_set = set(stale_belief_ids)
        if not stale_belief_id_set:
            return {"genes": [], "capsules": []}

        demoted_at = datetime.now(timezone.utc).isoformat()
        reconciled_gene_ids = {
            item.get("id")
            for item in self._fetch_genes()
            if item.get("source_fact_id") in stale_belief_id_set
            and item.get("is_stale")
        }

        if self.path is None:
            reconciled_genes = []
            for gene in self._genes:
                if gene.get("source_fact_id") not in stale_belief_id_set:
                    continue
                if gene.get("is_stale"):
                    continue
                gene["score"] = max(0, int(gene.get("score") or 0) - 1)
                gene["is_stale"] = True
                gene["demoted_at"] = demoted_at
                reconciled_gene_ids.add(gene["id"])
                reconciled_genes.append(gene)

            reconciled_capsules = []
            for capsule in self._capsules:
                capsule_gene_ids = set(capsule.get("gene_ids", []))
                if not capsule_gene_ids:
                    continue
                if capsule.get("is_stale"):
                    continue
                if not capsule_gene_ids.issubset(reconciled_gene_ids):
                    continue
                capsule["score"] = max(0, int(capsule.get("score") or 0) - 1)
                capsule["is_stale"] = True
                capsule["demoted_at"] = demoted_at
                reconciled_capsules.append(capsule)
            return {"genes": reconciled_genes, "capsules": reconciled_capsules}

        with self._connect() as connection:
            stale_gene_ids = {
                item.get("id")
                for item in self._fetch_genes()
                if item.get("is_stale") and item.get("id")
            }
            for gene in self._fetch_genes():
                if gene.get("source_fact_id") not in stale_belief_id_set:
                    continue
                if gene.get("is_stale"):
                    continue
                connection.execute(
                    "UPDATE genes SET score = CASE WHEN score > 0 THEN score - 1 ELSE 0 END, is_stale = 1, demoted_at = ? WHERE id = ?",
                    (demoted_at, gene["id"]),
                )
                reconciled_gene_ids.add(gene["id"])
                stale_gene_ids.add(gene["id"])
            for capsule in self._fetch_capsules():
                capsule_gene_ids = set(capsule.get("gene_ids", []))
                if not capsule_gene_ids:
                    continue
                if capsule.get("is_stale"):
                    continue
                if not capsule_gene_ids.issubset(stale_gene_ids):
                    continue
                connection.execute(
                    "UPDATE capsules SET score = CASE WHEN score > 0 THEN score - 1 ELSE 0 END, is_stale = 1, demoted_at = ? WHERE id = ?",
                    (demoted_at, capsule["id"]),
                )

        reconciled_genes = [
            item
            for item in self._fetch_genes()
            if item.get("id") in reconciled_gene_ids
            and item.get("demoted_at") == demoted_at
        ]
        reconciled_capsules = [
            item
            for item in self._fetch_capsules()
            if item.get("demoted_at") == demoted_at
            and set(item.get("gene_ids", [])).issubset(reconciled_gene_ids)
        ]
        return {"genes": reconciled_genes, "capsules": reconciled_capsules}

    def list_events(self, limit: int = 20) -> dict:
        events = self._fetch_events()
        return {"count": len(events[:limit]), "events": events[:limit]}

    def record_event(
        self,
        *,
        action: str,
        target_kind: str,
        target_id: str,
        rationale: str | None = None,
        source_record_id: str | None = None,
    ) -> dict:
        event = {
            "id": f"evt_{len(self._events) + 1:04d}",
            "action": action,
            "target_kind": target_kind,
            "target_id": target_id,
            "rationale": rationale,
            "source_record_id": source_record_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.path is None:
            self._events.append(event)
        else:
            existing_count = len(self._fetch_events())
            event["id"] = f"evt_{existing_count + 1:04d}"
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO evolution_events (id, action, target_kind, target_id, rationale, source_record_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        event["id"],
                        event["action"],
                        event["target_kind"],
                        event["target_id"],
                        event["rationale"],
                        event["source_record_id"],
                        event["created_at"],
                    ),
                )
        return event

    def apply_feedback(
        self,
        *,
        target_kind: str,
        target_id: str,
        signal: str,
        note: str | None = None,
    ) -> dict:
        signal_deltas = {
            "success": 2,
            "confirm": 1,
            "reject": -1,
            "correct": -2,
        }
        delta = signal_deltas.get(signal, 0)
        stale = delta < 0
        demoted_at = datetime.now(timezone.utc).isoformat() if stale else None

        if target_kind == "gene":
            records = self._fetch_genes()
            target = next(
                (item for item in records if item.get("id") == target_id), None
            )
            if target is None:
                raise KeyError(f"Unknown gene: {target_id}")
            updated = {
                **target,
                "score": int(target.get("score") or 0) + delta,
                "is_stale": stale if delta < 0 else False,
                "demoted_at": demoted_at if stale else None,
            }
            if self.path is None:
                for index, item in enumerate(self._genes):
                    if item.get("id") == target_id:
                        self._genes[index] = updated
                        break
            else:
                with self._connect() as connection:
                    connection.execute(
                        "UPDATE genes SET score = ?, is_stale = ?, demoted_at = ? WHERE id = ?",
                        (
                            updated["score"],
                            int(updated["is_stale"]),
                            updated["demoted_at"],
                            target_id,
                        ),
                    )
            return {**updated, "delta": delta, "note": note, "signal": signal}

        if target_kind == "capsule":
            records = self._fetch_capsules()
            target = next(
                (item for item in records if item.get("id") == target_id), None
            )
            if target is None:
                raise KeyError(f"Unknown capsule: {target_id}")
            updated = {
                **target,
                "score": int(target.get("score") or 0) + delta,
                "is_stale": stale if delta < 0 else False,
                "demoted_at": demoted_at if stale else None,
            }
            if self.path is None:
                for index, item in enumerate(self._capsules):
                    if item.get("id") == target_id:
                        self._capsules[index] = updated
                        break
            else:
                with self._connect() as connection:
                    connection.execute(
                        "UPDATE capsules SET score = ?, is_stale = ?, demoted_at = ? WHERE id = ?",
                        (
                            updated["score"],
                            int(updated["is_stale"]),
                            updated["demoted_at"],
                            target_id,
                        ),
                    )
            return {**updated, "delta": delta, "note": note, "signal": signal}

        raise KeyError(f"Unsupported feedback target kind: {target_kind}")


__all__ = ["GovernancePlaneService"]
