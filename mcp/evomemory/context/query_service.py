from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class ContextQueryService:
    def __init__(self, core: Any):
        self.core = core

    def health(self) -> dict[str, Any]:
        status = self.core.repository.status()
        return {"ok": True, **status}

    def debug_status(self) -> dict[str, Any]:
        payload = self.mcp_status()
        payload.update(self.core.state_store.summary())
        payload.update(self.core.repository.memory_stats())
        payload.update(self.core.runtime)
        return payload

    def search_context(
        self, query: str, directory: str, session_id: str | None = None
    ) -> dict[str, Any]:
        normalized_directory = self.core._normalize_directory(directory)
        wing = self.core.resolve_wing(directory)
        context_items, context_total_count, context_truncated_count = (
            self.core._tiered_context_results(
                query=query,
                directory=normalized_directory,
                wing=wing,
                session_id=session_id,
            )
        )
        results = [self.core._format_context_hit(item) for item in context_items]
        core_memory, core_memory_total_count, core_memory_truncated_count = (
            self.core._core_memory_results(normalized_directory, wing)
        )
        self.core.runtime["last_search_at"] = datetime.now(timezone.utc).isoformat()
        payload = {
            "session_id": session_id,
            "query": query,
            "directory": normalized_directory,
            "wing": wing,
            "core_memory": core_memory,
            "core_memory_total_count": core_memory_total_count,
            "core_memory_truncated_count": core_memory_truncated_count,
            "context_total_count": context_total_count,
            "context_truncated_count": context_truncated_count,
            "results_count": len(results),
            "results": results,
            "system_block": self.core._build_system_block(
                wing,
                results,
                core_memory,
                core_memory_truncated_count=core_memory_truncated_count,
                context_truncated_count=context_truncated_count,
            ),
        }
        return self.core.runtime_orchestrator.augment_context_payload(payload)

    def mcp_status(self) -> dict[str, Any]:
        payload = self.core.repository.status()
        payload.update(
            {
                "service": "mempalace-bridge",
                "state_path": str(self.core.config.state_path),
            }
        )
        return payload

    def mcp_list_wings(self) -> dict[str, Any]:
        return {"wings": self.core.repository.list_wings()}

    def mcp_list_rooms(self, wing: str | None = None) -> dict[str, Any]:
        try:
            safe_wing = self.core.sanitize_optional_name(wing, "wing")
        except ValueError as exc:
            return {"error": str(exc)}
        return {
            "wing": safe_wing or "all",
            "rooms": self.core.repository.list_rooms(wing=safe_wing),
        }

    def mcp_get_taxonomy(self) -> dict[str, Any]:
        return self.core.repository.get_taxonomy()

    def mcp_get_drawer(self, drawer_id: str) -> dict[str, Any]:
        result = self.core.repository.get_drawer(drawer_id)
        return result or {"error": f"Drawer not found: {drawer_id}"}

    def mcp_search(
        self,
        query: str,
        limit: int = 5,
        wing: str | None = None,
        memory_tier: str | None = None,
        current_only: bool = False,
        historical_only: bool = False,
        room: str | None = None,
    ) -> dict[str, Any]:
        try:
            safe_wing = self.core.sanitize_optional_name(wing, "wing")
            safe_memory_tier = self.core.sanitize_optional_memory_tier(memory_tier)
            safe_room = self.core.sanitize_optional_name(room, "room")
        except ValueError as exc:
            return {"error": str(exc)}
        results = [
            self.core._format_public_hit(item)
            for item in self.core.repository.query_drawers(
                query=query,
                wing=safe_wing,
                memory_tier=safe_memory_tier,
                current_only=current_only,
                historical_only=historical_only,
                room=safe_room,
                limit=self.core._normalize_limit(limit, default=5),
            )
            if item.get("text") and float(item.get("similarity", 0)) > 0
        ]
        return {
            "query": query,
            "wing": safe_wing,
            "memory_tier": safe_memory_tier,
            "current_only": current_only,
            "historical_only": historical_only,
            "room": safe_room,
            "results": results,
        }

    def mcp_list_drawers(
        self,
        wing: str | None = None,
        room: str | None = None,
        session_id: str | None = None,
        memory_tier: str | None = None,
        current_only: bool = False,
        historical_only: bool = False,
        role: str | None = None,
        source_file: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        try:
            safe_wing = self.core.sanitize_optional_name(wing, "wing")
            safe_room = self.core.sanitize_optional_name(room, "room")
            safe_memory_tier = self.core.sanitize_optional_memory_tier(memory_tier)
            safe_role = self.core.sanitize_optional_role(role)
        except ValueError as exc:
            return {"error": str(exc)}

        drawers = [
            self.core._format_public_hit(item)
            for item in self.core.repository.list_drawers(
                wing=safe_wing,
                room=safe_room,
                session_id=session_id,
                memory_tier=safe_memory_tier,
                current_only=current_only,
                historical_only=historical_only,
                role=safe_role,
                source_file=source_file,
                limit=self.core._normalize_limit(limit),
                offset=self.core._normalize_offset(offset),
            )
        ]
        return {
            "wing": safe_wing,
            "room": safe_room,
            "session_id": session_id,
            "memory_tier": safe_memory_tier,
            "current_only": current_only,
            "historical_only": historical_only,
            "role": safe_role,
            "source_file": source_file,
            "count": len(drawers),
            "offset": self.core._normalize_offset(offset),
            "limit": self.core._normalize_limit(limit),
            "drawers": drawers,
        }

    def mcp_list_sessions(
        self,
        wing: str | None = None,
        room: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        try:
            safe_wing = self.core.sanitize_optional_name(wing, "wing")
            safe_room = self.core.sanitize_optional_name(room, "room")
        except ValueError as exc:
            return {"error": str(exc)}

        sessions = self.core.repository.list_sessions(
            wing=safe_wing,
            room=safe_room,
            limit=self.core._normalize_limit(limit),
            offset=self.core._normalize_offset(offset),
        )
        return {
            "wing": safe_wing,
            "room": safe_room,
            "count": len(sessions),
            "offset": self.core._normalize_offset(offset),
            "limit": self.core._normalize_limit(limit),
            "sessions": sessions,
        }

    def mcp_get_session_messages(
        self,
        session_id: str,
        memory_tier: str | None = None,
        current_only: bool = False,
        historical_only: bool = False,
        role: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        try:
            safe_memory_tier = self.core.sanitize_optional_memory_tier(memory_tier)
            safe_role = self.core.sanitize_optional_role(role)
        except ValueError as exc:
            return {"error": str(exc)}

        messages = [
            self.core._format_public_hit(item)
            for item in self.core.repository.get_session_messages(
                session_id=session_id,
                memory_tier=safe_memory_tier,
                current_only=current_only,
                historical_only=historical_only,
                role=safe_role,
                limit=self.core._normalize_limit(limit),
                offset=self.core._normalize_offset(offset),
            )
        ]
        return {
            "session_id": session_id,
            "memory_tier": safe_memory_tier,
            "current_only": current_only,
            "historical_only": historical_only,
            "role": safe_role,
            "count": len(messages),
            "offset": self.core._normalize_offset(offset),
            "limit": self.core._normalize_limit(limit),
            "messages": messages,
        }

    def mcp_kg_query(
        self, entity: str, as_of: str | None = None, direction: str = "both"
    ) -> dict[str, Any]:
        return self.core.repository.kg_query(entity, as_of=as_of, direction=direction)


__all__ = ["ContextQueryService"]
