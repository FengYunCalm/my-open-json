from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


ARCHIVE_FORMAT = "evomemory-archive-v1"


class MemoryArchiveService:
    def __init__(self, core: Any):
        self.core = core

    def _list_archive_drawers(self, *, limit: int) -> list[dict[str, Any]]:
        rows = self.core.repository.list_drawers(limit=limit, offset=0)
        return [
            {
                "drawer_id": item.get("drawer_id"),
                "text": item.get("text", ""),
                "wing": item.get("wing"),
                "room": item.get("room"),
                "directory": item.get("directory"),
                "source_file": item.get("source_file"),
                "session_id": item.get("session_id"),
                "message_id": item.get("message_id"),
                "role": item.get("role"),
                "memory_tier": item.get("memory_tier"),
                "memory_key": item.get("memory_key"),
                "memory_value": item.get("memory_value"),
                "valid_from": item.get("valid_from"),
                "valid_to": item.get("valid_to"),
                "filed_at": item.get("filed_at"),
                "working_summary": item.get("working_summary") is True,
                "metadata": dict(item.get("metadata") or {}),
            }
            for item in rows
        ]

    def export_archive(self, *, limit: int = 20) -> dict[str, Any]:
        normalized_limit = self.core._normalize_limit(limit, default=20)
        governance = self.core.governance_service.export_state(limit=normalized_limit)
        evaluation = self.core.evaluation_service.export_state(limit=normalized_limit)
        drawers = self._list_archive_drawers(limit=normalized_limit)
        beliefs = self.core.belief_service.export_facts(limit=normalized_limit)
        archive = {
            "service": "evomemory",
            "format": ARCHIVE_FORMAT,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "limit": normalized_limit,
            "context": {
                "drawer_count": len(drawers),
                "drawers": drawers,
            },
            "belief": {
                "count": len(beliefs),
                "facts": beliefs,
            },
            "governance": {
                "gene_count": len(governance["genes"]),
                "genes": governance["genes"],
                "capsule_count": len(governance["capsules"]),
                "capsules": governance["capsules"],
                "event_count": len(governance["events"]),
                "events": governance["events"],
            },
            "evaluation": {
                "metrics": evaluation["metrics"],
            },
            "feedback": {
                "count": len(evaluation["feedback"]),
                "records": evaluation["feedback"],
            },
            "runtime": dict(self.core.runtime),
            "maintenance_summary": self.core.maintenance_summary(),
        }
        archive["summary"] = {
            "drawer_count": archive["context"]["drawer_count"],
            "belief_count": archive["belief"]["count"],
            "gene_count": archive["governance"]["gene_count"],
            "capsule_count": archive["governance"]["capsule_count"],
            "event_count": archive["governance"]["event_count"],
            "feedback_count": archive["feedback"]["count"],
            "metric_count": len(archive["evaluation"]["metrics"]),
        }
        return archive

    def _merge_runtime(self, runtime_payload: dict[str, Any]) -> None:
        for key, value in (runtime_payload or {}).items():
            current = self.core.runtime.get(key)
            if key.endswith("_at") and isinstance(value, str):
                if not current or value > current:
                    self.core.runtime[key] = value
                continue
            if current in (None, "", [], {}, 0):
                self.core.runtime[key] = value

    def import_archive(
        self,
        archive: dict[str, Any],
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(archive, dict):
            raise ValueError("archive must be an object")
        if archive.get("format") != ARCHIVE_FORMAT:
            raise ValueError(f"unsupported archive format: {archive.get('format')}")

        drawers = list((archive.get("context") or {}).get("drawers") or [])
        facts = list((archive.get("belief") or {}).get("facts") or [])
        governance = archive.get("governance") or {}
        genes = list(governance.get("genes") or [])
        capsules = list(governance.get("capsules") or [])
        events = list(governance.get("events") or [])
        metrics = dict((archive.get("evaluation") or {}).get("metrics") or {})
        feedback = list((archive.get("feedback") or {}).get("records") or [])
        runtime_payload = dict(archive.get("runtime") or {})

        existing_drawer_ids = {
            item.get("drawer_id")
            for item in self.core.repository.list_drawers(limit=1000, offset=0)
            if item.get("drawer_id")
        }
        existing_belief_ids = {
            item.get("id")
            for item in self.core.belief_service.export_facts(limit=None)
            if item.get("id")
        }
        governance_state = self.core.governance_service.export_state(limit=None)
        existing_gene_ids = {
            item.get("id") for item in governance_state["genes"] if item.get("id")
        }
        existing_capsule_ids = {
            item.get("id") for item in governance_state["capsules"] if item.get("id")
        }
        existing_event_ids = {
            item.get("id") for item in governance_state["events"] if item.get("id")
        }
        evaluation_state = self.core.evaluation_service.export_state(limit=None)
        existing_feedback_ids = {
            item.get("id") for item in evaluation_state["feedback"] if item.get("id")
        }

        new_drawers = [item for item in drawers if item.get("drawer_id") not in existing_drawer_ids]
        new_facts = [item for item in facts if item.get("id") not in existing_belief_ids]
        new_genes = [item for item in genes if item.get("id") not in existing_gene_ids]
        new_capsules = [item for item in capsules if item.get("id") not in existing_capsule_ids]
        new_events = [item for item in events if item.get("id") not in existing_event_ids]
        new_feedback = [item for item in feedback if item.get("id") not in existing_feedback_ids]

        summary = {
            "drawers": {"total": len(drawers), "new": len(new_drawers), "existing": len(drawers) - len(new_drawers)},
            "beliefs": {"total": len(facts), "new": len(new_facts), "existing": len(facts) - len(new_facts)},
            "genes": {"total": len(genes), "new": len(new_genes), "existing": len(genes) - len(new_genes)},
            "capsules": {"total": len(capsules), "new": len(new_capsules), "existing": len(capsules) - len(new_capsules)},
            "events": {"total": len(events), "new": len(new_events), "existing": len(events) - len(new_events)},
            "feedback": {"total": len(feedback), "new": len(new_feedback), "existing": len(feedback) - len(new_feedback)},
            "metrics": {"total": len(metrics), "merged": len(metrics)},
            "runtime_keys": {"total": len(runtime_payload)},
        }

        if dry_run:
            return {
                "service": "evomemory",
                "format": ARCHIVE_FORMAT,
                "dry_run": True,
                "summary": summary,
            }

        imported_drawers = self.core.repository.import_drawers(new_drawers)
        imported_facts = self.core.belief_service.upsert_facts(new_facts)
        imported_genes = self.core.governance_service.upsert_genes(new_genes)
        imported_capsules = self.core.governance_service.upsert_capsules(new_capsules)
        imported_events = self.core.governance_service.upsert_events(new_events)
        merged_metrics = self.core.evaluation_service.merge_metrics(metrics)
        imported_feedback = self.core.evaluation_service.upsert_feedback(new_feedback)
        self._merge_runtime(runtime_payload)
        self.core._persist_runtime_state()

        return {
            "service": "evomemory",
            "format": ARCHIVE_FORMAT,
            "dry_run": False,
            "summary": summary,
            "imported": {
                "drawers": imported_drawers,
                "beliefs": imported_facts,
                "genes": imported_genes,
                "capsules": imported_capsules,
                "events": imported_events,
                "metrics": merged_metrics,
                "feedback": imported_feedback,
            },
        }


__all__ = ["ARCHIVE_FORMAT", "MemoryArchiveService"]
