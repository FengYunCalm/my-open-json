from __future__ import annotations

from datetime import datetime
from typing import Any


def _timestamp_score(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _belief_sort_key(item: dict[str, Any]) -> tuple[float, int, float, int, str]:
    scope_priority = 1 if item.get("scope") == "user" else 0
    return (
        float(item.get("confidence") or 0.0),
        int(item.get("source_count") or 0),
        _timestamp_score(item.get("last_confirmed_at") or item.get("valid_from")),
        scope_priority,
        item.get("key") or "",
    )


def _governance_sort_key(item: dict[str, Any]) -> tuple[int, float, int, str]:
    scope_priority = 1 if item.get("scope") == "user" else 0
    return (
        int(item.get("score") or 0),
        _timestamp_score(item.get("updated_at") or item.get("created_at")),
        scope_priority,
        item.get("key") or item.get("id") or "",
    )


def _trim_line(line: str, max_chars: int | None) -> str:
    if max_chars is None:
        return line
    if max_chars <= 3:
        return ""
    if len(line) <= max_chars:
        return line
    return f"{line[: max_chars - 3]}..."


def _trim_trailing_blank_lines(lines: list[str]) -> None:
    while lines and not lines[-1].strip():
        lines.pop()


def _trim_trailing_empty_titles(lines: list[str]) -> None:
    _trim_trailing_blank_lines(lines)
    while lines and lines[-1].endswith(":"):
        lines.pop()
        _trim_trailing_blank_lines(lines)


class RuntimeOrchestrator:
    def __init__(self, core: Any, evaluation_service: Any | None = None):
        self.core = core
        self.evaluation_service = evaluation_service

    def _config_int(self, name: str, default: int = 0) -> int:
        config = getattr(self.core, "config", None)
        value = getattr(config, name, default)
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            return default
        return max(0, normalized)

    def _max_block_chars(self) -> int | None:
        config = getattr(self.core, "config", None)
        limit = getattr(config, "max_block_chars", None)
        if limit is None:
            return None
        try:
            normalized = int(limit)
        except (TypeError, ValueError):
            return None
        return normalized if normalized > 0 else None

    def _append_overlay_section(
        self,
        block: str,
        title: str,
        entries: list[str],
        omitted_label: str,
    ) -> str:
        if not entries:
            return block

        limit = self._max_block_chars()
        separator = "\n\n" if block else ""
        titled_block = f"{block}{separator}{title}"
        if limit is not None and len(titled_block) > limit:
            return block
        block = titled_block

        included = 0
        for entry in entries:
            remaining = None if limit is None else limit - len(block) - 1
            line = _trim_line(entry, remaining)
            if not line:
                break
            candidate = f"{block}\n{line}"
            if limit is not None and len(candidate) > limit:
                break
            block = candidate
            included += 1

        omitted = len(entries) - included
        if omitted <= 0:
            return block

        notice = f"   ... {omitted} more {omitted_label} omitted"
        candidate = f"{block}\n{notice}"
        if limit is None or len(candidate) <= limit:
            return candidate
        return block

    def _reserve_budget_for_overlay(
        self,
        block: str,
        title: str,
        entries: list[str],
    ) -> str:
        if not block or not entries:
            return block

        limit = self._max_block_chars()
        if limit is None:
            return block

        minimum_cost = (2 if block else 0) + len(title) + 1 + len(entries[0])
        if minimum_cost > limit:
            return block

        reserve_target = max(
            minimum_cost,
            min(limit, self._config_int("runtime_overlay_reserved_chars", 0)),
        )
        base_floor = min(
            limit,
            self._config_int("runtime_base_min_chars", 0),
        )

        if len(block) + reserve_target <= limit:
            return block

        def trim_to_target(target_free_chars: int, enforce_floor: bool) -> str | None:
            lines = block.splitlines()
            while True:
                candidate_block = "\n".join(lines)
                if len(candidate_block) + target_free_chars <= limit and (
                    not enforce_floor or len(candidate_block) >= base_floor
                ):
                    return candidate_block
                if not lines:
                    return None
                lines.pop()
                _trim_trailing_empty_titles(lines)

        candidate = trim_to_target(reserve_target, enforce_floor=True)
        if candidate is not None:
            return candidate

        candidate = trim_to_target(minimum_cost, enforce_floor=True)
        if candidate is not None:
            return candidate

        candidate = trim_to_target(minimum_cost, enforce_floor=False)
        if candidate is not None:
            return candidate

        return block

    def _belief_memory(
        self, payload: dict[str, Any], limit: int = 6
    ) -> list[dict[str, Any]]:
        selected_keys = [
            item.get("memory_key")
            for item in payload.get("core_memory", [])
            if item.get("memory_key")
        ]
        if not selected_keys:
            facts = self.core.evomemory_query_beliefs(
                current_only=True,
                limit=max(limit * 4, 20),
            )["facts"]
            return sorted(facts, key=_belief_sort_key, reverse=True)[:limit]

        facts = []
        seen = set()
        for memory_key in selected_keys:
            belief = self.core.evomemory_query_beliefs(
                key=memory_key,
                current_only=True,
                limit=1,
            )["facts"]
            if not belief:
                continue
            fact = belief[0]
            if fact["id"] in seen:
                continue
            seen.add(fact["id"])
            facts.append(fact)
        return sorted(facts, key=_belief_sort_key, reverse=True)[:limit]

    def _governance_assets(
        self,
        belief_memory: list[dict[str, Any]],
        gene_limit: int = 6,
        capsule_limit: int = 4,
    ) -> dict[str, Any]:
        genes = self.core.evomemory_query_genes(limit=max(gene_limit * 4, 20))["genes"]
        capsules = self.core.evomemory_query_capsules(limit=max(capsule_limit * 4, 20))[
            "capsules"
        ]
        genes = [item for item in genes if not item.get("is_stale")]
        capsules = [item for item in capsules if not item.get("is_stale")]
        belief_keys = {item.get("key") for item in belief_memory if item.get("key")}
        belief_scopes = {
            item.get("scope") for item in belief_memory if item.get("scope")
        }
        if belief_keys:
            genes = [item for item in genes if item.get("key") in belief_keys]
        if belief_scopes:
            capsules = [item for item in capsules if item.get("scope") in belief_scopes]
        genes = sorted(genes, key=_governance_sort_key, reverse=True)[:gene_limit]
        capsules = sorted(capsules, key=_governance_sort_key, reverse=True)[
            :capsule_limit
        ]
        return {
            "gene_count": len(genes),
            "genes": genes,
            "capsule_count": len(capsules),
            "capsules": capsules,
        }

    def _augment_system_block(
        self,
        base_block: str,
        belief_memory: list[dict[str, Any]],
        governance_assets: dict[str, Any],
    ) -> str:
        block = base_block or ""
        if belief_memory:
            belief_entries = [
                f"{index}. [{item.get('scope')}] {item.get('key')}={item.get('value')}"
                for index, item in enumerate(belief_memory, start=1)
            ]
            block = self._reserve_budget_for_overlay(
                block,
                "Belief memory:",
                belief_entries,
            )
            block = self._append_overlay_section(
                block,
                "Belief memory:",
                belief_entries,
                "belief memories",
            )
        genes = governance_assets.get("genes", [])
        capsules = governance_assets.get("capsules", [])
        if genes or capsules:
            governance_entries = [
                f"- gene[{gene.get('scope')}] {gene.get('key')}={gene.get('value')}"
                for gene in genes
            ] + [
                f"- capsule[{capsule.get('scope')}] genes={','.join(capsule.get('gene_ids', []))}"
                for capsule in capsules
            ]
            if not belief_memory:
                block = self._reserve_budget_for_overlay(
                    block,
                    "Governance assets:",
                    governance_entries,
                )
            block = self._append_overlay_section(
                block,
                "Governance assets:",
                governance_entries,
                "governance assets",
            )
        return block

    def augment_context_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.evaluation_service is not None:
            self.evaluation_service.increment("search_context_calls")
        belief_memory = self._belief_memory(payload)
        governance_assets = self._governance_assets(belief_memory)
        asset_updates = self.core.governance_service.touch_assets(
            gene_ids=[
                item.get("id")
                for item in governance_assets.get("genes", [])
                if item.get("id")
            ],
            capsule_ids=[
                item.get("id")
                for item in governance_assets.get("capsules", [])
                if item.get("id")
            ],
        )
        if self.evaluation_service is not None and (
            belief_memory
            or governance_assets.get("genes")
            or governance_assets.get("capsules")
        ):
            self.evaluation_service.increment("enriched_searches")
            if asset_updates.get("gene_updates"):
                self.evaluation_service.increment(
                    "gene_score_updates", asset_updates["gene_updates"]
                )
            if asset_updates.get("capsule_updates"):
                self.evaluation_service.increment(
                    "capsule_score_updates", asset_updates["capsule_updates"]
                )
        if asset_updates.get("gene_updates") or asset_updates.get("capsule_updates"):
            governance_assets = self._governance_assets(belief_memory)
        return {
            **payload,
            "belief_memory_count": len(belief_memory),
            "belief_memory": belief_memory,
            "governance_assets": governance_assets,
            "system_block": self._augment_system_block(
                payload.get("system_block", ""),
                belief_memory,
                governance_assets,
            ),
        }


__all__ = ["RuntimeOrchestrator"]
