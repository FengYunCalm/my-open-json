from __future__ import annotations

from typing import Any


class MemoryReviser:
    def __init__(self, repository: Any):
        self.repository = repository

    def revise_memory(
        self,
        *,
        wing: str,
        directory: str,
        memory_tier: str,
        memory_key: str,
        memory_value: str,
        valid_to: str,
    ) -> dict[str, Any]:
        current_memories = self.repository.query_drawers(
            query=None,
            wing=wing,
            directory=directory,
            memory_tier=memory_tier,
            current_only=True,
            limit=20,
        )
        current_match = next(
            (item for item in current_memories if item.get("memory_key") == memory_key),
            None,
        )
        if current_match and current_match.get("memory_value") == memory_value:
            return {
                "skip_save": True,
                "reason": "duplicate_value",
                "current_match": current_match,
                "invalidated_count": 0,
            }

        invalidated_count = self.repository.invalidate_memory_conflicts(
            wing=wing,
            directory=directory,
            memory_tier=memory_tier,
            memory_key=memory_key,
            valid_to=valid_to,
        )
        return {
            "skip_save": False,
            "reason": None,
            "current_match": current_match,
            "invalidated_count": invalidated_count,
        }


__all__ = ["MemoryReviser"]
