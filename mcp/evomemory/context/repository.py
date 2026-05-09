from __future__ import annotations

from typing import Any


class ContextRepository:
    def __init__(self, backend: Any):
        self.backend = backend

    def query_drawers(self, **kwargs):
        return self.backend.query_drawers(**kwargs)

    def keyword_query_drawers(self, **kwargs):
        query = getattr(self.backend, "keyword_query_drawers", None)
        if callable(query):
            return query(**kwargs)
        return []

    def get_session_messages(self, **kwargs):
        return self.backend.get_session_messages(**kwargs)

    def save_entry(self, **kwargs):
        return self.backend.save_entry(**kwargs)

    def import_drawers(self, drawers: list[dict[str, Any]]):
        importer = getattr(self.backend, "import_drawers", None)
        if callable(importer):
            return importer(drawers)

        imported = []
        skipped = 0
        getter = getattr(self.backend, "get_drawer", None)
        for item in drawers:
            drawer_id = item.get("drawer_id")
            if callable(getter) and drawer_id and getter(drawer_id) is not None:
                skipped += 1
                continue
            payload = self.backend.save_entry(
                wing=item.get("wing") or "unknown",
                room=item.get("room") or "unknown",
                content=item.get("text") or item.get("content") or "",
                source_file=item.get("source_file") or "archive:unknown",
                metadata=dict(item.get("metadata") or {}),
            )
            imported.append(payload)
        return {
            "imported_count": len(imported),
            "skipped_count": skipped,
            "drawers": imported,
        }

    def invalidate_memory_conflicts(self, **kwargs):
        return self.backend.invalidate_memory_conflicts(**kwargs)

    def invalidate_drawers(self, **kwargs):
        return self.backend.invalidate_drawers(**kwargs)

    def delete_drawers(self, **kwargs):
        deleter = getattr(self.backend, "delete_drawers", None)
        if callable(deleter):
            return deleter(**kwargs)
        return 0

    def list_stale_drawer_ids(self, **kwargs):
        lister = getattr(self.backend, "list_stale_drawer_ids", None)
        if callable(lister):
            return lister(**kwargs)
        return []

    def status(self):
        return self.backend.status()

    def memory_stats(self):
        return self.backend.memory_stats()

    def list_wings(self):
        return self.backend.list_wings()

    def list_rooms(self, **kwargs):
        return self.backend.list_rooms(**kwargs)

    def get_taxonomy(self):
        return self.backend.get_taxonomy()

    def list_drawers(self, **kwargs):
        return self.backend.list_drawers(**kwargs)

    def get_drawer(self, drawer_id: str):
        return self.backend.get_drawer(drawer_id)

    def list_sessions(self, **kwargs):
        return self.backend.list_sessions(**kwargs)

    def kg_query(self, entity: str, as_of: str | None = None, direction: str = "both"):
        return self.backend.kg_query(entity, as_of=as_of, direction=direction)


__all__ = ["ContextRepository"]
