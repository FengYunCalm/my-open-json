from __future__ import annotations

from dataclasses import MISSING, fields
import re
from datetime import datetime, timezone
from typing import Any


class ContextQueryService:
    _BUDGET_POLICY_KEYS = (
        "max_block_chars",
        "runtime_overlay_reserved_chars",
        "runtime_base_min_chars",
    )

    def __init__(self, core: Any):
        self.core = core

    def _budget_policy_summary(self) -> dict[str, int | None]:
        config = self.core.config
        return {key: getattr(config, key, None) for key in self._BUDGET_POLICY_KEYS}

    def _budget_policy_diff(self) -> dict[str, dict[str, int | None]]:
        config = self.core.config
        defaults: dict[str, int | None] = {}
        for field in fields(config):
            if field.name not in self._BUDGET_POLICY_KEYS:
                continue
            defaults[field.name] = (
                field.default if field.default is not MISSING else None
            )

        diff: dict[str, dict[str, int | None]] = {}
        for key, current in self._budget_policy_summary().items():
            default = defaults.get(key)
            if current == default:
                continue
            delta = None
            if isinstance(current, int) and isinstance(default, int):
                delta = current - default
            diff[key] = {
                "default": default,
                "current": current,
                "delta": delta,
            }
        return diff

    def _displayed_runtime_overlay(self, system_block: str) -> dict[str, list[str]]:
        belief_keys: list[str] = []
        gene_keys: list[str] = []
        capsule_scopes: list[str] = []
        section: str | None = None
        for raw_line in system_block.splitlines():
            line = raw_line.strip()
            if line == "Belief memory:":
                section = "belief"
                continue
            if line == "Governance assets:":
                section = "governance"
                continue
            if line.endswith(":") and line not in {
                "Belief memory:",
                "Governance assets:",
            }:
                section = None
                continue
            if not line or line.startswith("..."):
                continue
            if section == "belief":
                match = re.match(r"^\d+\. \[[^\]]+\] ([^=]+)=", line)
                if match:
                    belief_keys.append(match.group(1))
                continue
            if section == "governance":
                gene_match = re.match(r"^- gene\[[^\]]+\] ([^=]+)=", line)
                if gene_match:
                    gene_keys.append(gene_match.group(1))
                    continue
                capsule_match = re.match(r"^- capsule\[([^\]]+)\] ", line)
                if capsule_match:
                    capsule_scopes.append(capsule_match.group(1))
        return {
            "displayed_belief_keys": belief_keys,
            "displayed_governance_gene_keys": gene_keys,
            "displayed_capsule_scopes": capsule_scopes,
        }

    def _record_runtime_context(self, payload: dict[str, Any]) -> None:
        displayed = self._displayed_runtime_overlay(payload.get("system_block", ""))
        self.core.runtime["last_search_summary"] = {
            "query": payload.get("query"),
            "session_id": payload.get("session_id"),
            "system_block_length": len(payload.get("system_block", "")),
            "system_block_char_limit": getattr(
                self.core.config, "max_block_chars", None
            ),
            "belief_memory_keys": [
                item.get("key")
                for item in payload.get("belief_memory", [])
                if item.get("key")
            ],
            "governance_gene_keys": [
                item.get("key")
                for item in payload.get("governance_assets", {}).get("genes", [])
                if item.get("key")
            ],
            "capsule_scopes": [
                item.get("scope")
                for item in payload.get("governance_assets", {}).get("capsules", [])
                if item.get("scope")
            ],
            **displayed,
        }

    def health(self) -> dict[str, Any]:
        status = self.core.repository.status()
        return {"ok": True, **status}

    def debug_status(self) -> dict[str, Any]:
        payload = self.mcp_status()
        payload.update(self.core.state_store.summary())
        payload.update(self.core.repository.memory_stats())
        payload.update(self.core.runtime)
        payload["maintenance_summary"] = self.core.maintenance_summary()
        return payload

    def search_context(
        self,
        query: str,
        directory: str,
        session_id: str | None = None,
        include_trace: bool = False,
    ) -> dict[str, Any]:
        normalized_directory = self.core._normalize_directory(directory)
        wing = self.core.resolve_wing(directory)
        context_items, context_total_count, context_truncated_count, retrieval_trace = (
            self.core.retrieval_service.search_context(
                query=query,
                directory=normalized_directory,
                wing=wing,
                session_id=session_id,
                include_trace=include_trace,
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
        if retrieval_trace is not None:
            payload["retrieval_trace"] = retrieval_trace
        result = self.core.runtime_orchestrator.augment_context_payload(payload)
        self._record_runtime_context(result)
        self.core._persist_runtime_state()
        return result

    def mcp_status(self) -> dict[str, Any]:
        payload = self.core.repository.status()
        payload.update(
            {
                "service": "evomemory-bridge",
                "state_path": str(self.core.config.state_path),
                "budget_policy": self._budget_policy_summary(),
                "budget_policy_diff": self._budget_policy_diff(),
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
        include_trace: bool = False,
    ) -> dict[str, Any]:
        try:
            safe_wing = self.core.sanitize_optional_name(wing, "wing")
            safe_memory_tier = self.core.sanitize_optional_memory_tier(memory_tier)
            safe_room = self.core.sanitize_optional_name(room, "room")
        except ValueError as exc:
            return {"error": str(exc)}
        normalized_limit = self.core._normalize_limit(limit, default=5)
        rows, candidate_count, truncated_count, retrieval_trace = (
            self.core.retrieval_service.search_drawers(
                query=query,
                limit=normalized_limit,
                wing=safe_wing,
                memory_tier=safe_memory_tier,
                current_only=current_only,
                historical_only=historical_only,
                room=safe_room,
                include_trace=include_trace,
            )
        )
        payload = {
            "query": query,
            "wing": safe_wing,
            "memory_tier": safe_memory_tier,
            "current_only": current_only,
            "historical_only": historical_only,
            "room": safe_room,
            "count": len(rows),
            "candidate_count": candidate_count,
            "truncated_count": truncated_count,
            "results": [self.core._format_public_hit(item) for item in rows],
        }
        if retrieval_trace is not None:
            payload["retrieval_trace"] = retrieval_trace
        return payload

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
