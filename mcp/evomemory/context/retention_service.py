from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


class ContextRetentionService:
    def __init__(self, core: Any):
        self.core = core

    def _normalize_window_days(self, window_days: int | None) -> int:
        value = (
            self.core.config.retention_window_days
            if window_days is None
            else window_days
        )
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return max(0, int(self.core.config.retention_window_days or 0))

    def _current_referenced_record_ids(self) -> set[str]:
        return {
            item.get("source_record_id")
            for item in self.core.belief_service.export_facts(limit=None)
            if item.get("source_record_id") and not item.get("valid_to")
        }

    def run_retention(
        self,
        *,
        dry_run: bool = True,
        safe: bool | None = None,
        window_days: int | None = None,
    ) -> dict[str, Any]:
        normalized_dry_run = bool(dry_run)
        normalized_safe = (
            bool(self.core.config.retention_safe_default)
            if safe is None
            else bool(safe)
        )
        normalized_window_days = self._normalize_window_days(window_days)
        before = (
            datetime.now(timezone.utc) - timedelta(days=normalized_window_days)
        ).isoformat()

        candidate_ids = list(
            dict.fromkeys(self.core.repository.list_stale_drawer_ids(before=before))
        )
        referenced_ids = self._current_referenced_record_ids()
        retained_current_ids: list[str] = []
        retained_referenced_ids: list[str] = []
        purgeable_ids: list[str] = []

        for drawer_id in candidate_ids:
            drawer = self.core.repository.get_drawer(drawer_id) or {}
            metadata = dict(drawer.get("metadata") or {})
            if normalized_safe:
                is_current = not metadata.get("valid_to")
                is_referenced = drawer_id in referenced_ids
                if is_current:
                    retained_current_ids.append(drawer_id)
                if is_referenced:
                    retained_referenced_ids.append(drawer_id)
                if is_current or is_referenced:
                    continue
            purgeable_ids.append(drawer_id)

        deleted_count = 0
        deleted_ids: list[str] = []
        if not normalized_dry_run and purgeable_ids:
            deleted_count = int(
                self.core.repository.delete_drawers(drawer_ids=purgeable_ids) or 0
            )
            deleted_ids = purgeable_ids[:deleted_count]

        retention_at = datetime.now(timezone.utc).isoformat()
        self.core.runtime["last_retention_at"] = retention_at
        self.core.runtime["last_retention_before"] = before
        self.core.runtime["last_retention_window_days"] = normalized_window_days
        self.core.runtime["last_retention_candidate_count"] = len(candidate_ids)
        self.core.runtime["last_retention_purgeable_count"] = len(purgeable_ids)
        self.core.runtime["last_retention_deleted_count"] = deleted_count
        self.core.runtime["last_retention_safe"] = normalized_safe
        self.core.runtime["last_retention_dry_run"] = normalized_dry_run
        self.core._persist_runtime_state()

        self.core.evaluation_service.increment("retention_runs")
        if normalized_dry_run:
            self.core.evaluation_service.increment("retention_dry_runs")
        else:
            self.core.evaluation_service.increment("retention_delete_runs")
            if deleted_count:
                self.core.evaluation_service.increment(
                    "purged_context_drawers", deleted_count
                )
            if retained_current_ids:
                self.core.evaluation_service.increment(
                    "retained_current_context_drawers", len(retained_current_ids)
                )
            if retained_referenced_ids:
                self.core.evaluation_service.increment(
                    "retained_referenced_context_drawers",
                    len(retained_referenced_ids),
                )

        return {
            "service": "evomemory",
            "plane": "maintenance",
            "dry_run": normalized_dry_run,
            "safe": normalized_safe,
            "window_days": normalized_window_days,
            "before": before,
            "candidate_count": len(candidate_ids),
            "candidate_drawer_ids": candidate_ids,
            "protected_current_count": len(retained_current_ids),
            "protected_current_drawer_ids": retained_current_ids,
            "protected_referenced_count": len(retained_referenced_ids),
            "protected_referenced_drawer_ids": retained_referenced_ids,
            "purgeable_count": len(purgeable_ids),
            "purgeable_drawer_ids": purgeable_ids,
            "deleted_count": deleted_count,
            "deleted_drawer_ids": deleted_ids,
            "maintenance_summary": self.core.maintenance_summary(),
        }


__all__ = ["ContextRetentionService"]
