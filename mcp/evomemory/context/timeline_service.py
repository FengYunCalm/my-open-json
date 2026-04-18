from __future__ import annotations

from datetime import datetime
from typing import Any


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class MemoryTimelineService:
    def __init__(self, core: Any):
        self.core = core

    def _timeline_entry_for_belief(self, belief: dict[str, Any]) -> dict[str, Any]:
        return {
            "kind": "belief",
            "id": belief.get("id"),
            "timestamp": belief.get("valid_from"),
            "scope": belief.get("scope"),
            "key": belief.get("key"),
            "value": belief.get("value"),
            "state": "historical" if belief.get("valid_to") else "current",
        }

    def _timeline_entry_for_event(self, event: dict[str, Any]) -> dict[str, Any]:
        return {
            "kind": "event",
            "id": event.get("id"),
            "timestamp": event.get("created_at"),
            "action": event.get("action"),
            "target_kind": event.get("target_kind"),
            "target_id": event.get("target_id"),
            "rationale": event.get("rationale"),
        }

    def query_timeline(
        self,
        *,
        scope: str | None = None,
        key: str,
        as_of: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        belief_limit = max(20, int(limit) * 4)
        beliefs = self.core.belief_service.query(
            scope=scope,
            key=key,
            limit=belief_limit,
        ).get("facts", [])
        current_belief = next((item for item in beliefs if not item.get("valid_to")), None)
        belief_at_as_of = None
        if as_of is not None:
            belief_at_as_of = next(
                iter(
                    self.core.belief_service.query(
                        scope=scope,
                        key=key,
                        as_of=as_of,
                        limit=1,
                    ).get("facts", [])
                ),
                None,
            )

        genes = self.core.governance_service.list_genes(
            scope=scope,
            key=key,
            limit=belief_limit,
        ).get("genes", [])
        related_gene_ids = {item.get("id") for item in genes if item.get("id")}

        capsules = [
            item
            for item in self.core.governance_service.list_capsules(
                scope=scope,
                limit=belief_limit,
            ).get("capsules", [])
            if related_gene_ids.intersection(set(item.get("gene_ids", [])))
        ]
        related_capsule_ids = {item.get("id") for item in capsules if item.get("id")}

        related_target_ids = {
            item.get("id")
            for item in beliefs
            if item.get("id")
        } | related_gene_ids | related_capsule_ids
        events = [
            item
            for item in self.core.governance_service.list_events(limit=max(40, limit * 8)).get(
                "events", []
            )
            if item.get("target_id") in related_target_ids
        ]

        timeline = [
            self._timeline_entry_for_belief(item) for item in beliefs
        ] + [self._timeline_entry_for_event(item) for item in events]
        timeline = sorted(
            timeline,
            key=lambda item: (
                _parse_timestamp(item.get("timestamp")) or datetime.min,
                item.get("id") or "",
            ),
            reverse=True,
        )

        return {
            "scope": scope,
            "key": key,
            "as_of": as_of,
            "count": len(beliefs[:limit]),
            "beliefs": beliefs[:limit],
            "genes": genes[:limit],
            "capsules": capsules[:limit],
            "events": events[:limit],
            "timeline": timeline[:limit],
            "current_belief": current_belief,
            "belief_at_as_of": belief_at_as_of,
        }


__all__ = ["MemoryTimelineService"]
