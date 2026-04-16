from __future__ import annotations

from typing import Any


class ContextRepository:
    def __init__(self, backend: Any):
        self.backend = backend

    def query_drawers(self, **kwargs):
        return self.backend.query_drawers(**kwargs)

    def get_session_messages(self, **kwargs):
        return self.backend.get_session_messages(**kwargs)

    def save_entry(self, **kwargs):
        return self.backend.save_entry(**kwargs)

    def invalidate_memory_conflicts(self, **kwargs):
        return self.backend.invalidate_memory_conflicts(**kwargs)

    def invalidate_drawers(self, **kwargs):
        return self.backend.invalidate_drawers(**kwargs)

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
