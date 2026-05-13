from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from evomemory.domain.memory_policy import (
    MEMORY_CONTRACT_STATUS_NOT_APPLICABLE,
    MEMORY_CONTRACT_STATUS_TRUSTED,
    assess_memory_contract,
)


TOKEN_PATTERN = re.compile(r"[a-z0-9_]+|[\u4e00-\u9fff]+", re.IGNORECASE)
TIER_SCORE = {
    "session": 1.0,
    "directory": 0.8,
    "wing": 0.6,
    "global": 0.4,
    "filtered": 0.5,
}
LOW_OVERLAP_THRESHOLD = 0.2
LOW_CONFIDENCE_THRESHOLD = 0.35
LOW_SOURCE_COUNT_THRESHOLD = 2
LOW_OVERLAP_PENALTY = 0.09
SEMANTIC_ONLY_PENALTY = 0.07
LOW_CONFIDENCE_PENALTY = 0.05
LOW_SOURCE_COUNT_PENALTY = 0.025
HIGH_CONFIDENCE_BONUS = 0.03
HIGH_SOURCE_COUNT_BONUS = 0.02
MAX_SOURCE_COUNT = 4


def _tokenize(text: str | None) -> list[str]:
    normalized = (text or "").replace("_", " ").lower()
    return TOKEN_PATTERN.findall(normalized)


def _normalized_text(text: str | None) -> str:
    return " ".join((text or "").lower().split())


def _timestamp_score(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(value, upper))


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class ContextRetrievalService:
    def __init__(self, core: Any):
        self.core = core

    def _apply_context_contract(
        self,
        item: dict[str, Any],
        *,
        directory: str,
        wing: str,
    ) -> dict[str, Any] | None:
        contract = assess_memory_contract(
            item,
            current_directory=directory,
            current_wing=wing,
        )
        if contract["status"] == MEMORY_CONTRACT_STATUS_NOT_APPLICABLE:
            return item
        normalized = {
            **item,
            "directory": contract["directory"],
            "wing": contract["wing"],
            "session_id": contract["session_id"],
            "message_id": contract["message_id"],
            "source_file": contract["source_file"],
            "filed_at": contract["filed_at"],
            "valid_from": contract["valid_from"],
            "valid_to": contract["valid_to"],
            "confidence": contract["confidence"],
            "source_count": contract["source_count"],
            "superseded_by": contract["superseded_by"],
            "memory_contract": contract,
            "contract_status": contract["status"],
            "_contract_eligible": contract["status"] == MEMORY_CONTRACT_STATUS_TRUSTED,
        }
        return normalized

    def _candidate_limit(self, limit: int) -> int:
        return max(limit * 8, 20)

    def _keyword_candidate_limit(self, limit: int) -> int:
        return max(self._candidate_limit(limit) * 4, 100)

    def _keyword_overlap(
        self, query: str, item: dict[str, Any]
    ) -> tuple[float, list[str]]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return 0.0, []

        text_tokens = set(
            _tokenize(item.get("text"))
            + _tokenize(item.get("preview"))
            + _tokenize(item.get("memory_key"))
            + _tokenize(item.get("memory_value"))
        )
        matched = [token for token in query_tokens if token in text_tokens]
        return len(set(matched)) / len(set(query_tokens)), sorted(set(matched))

    def _memory_key_match(self, query: str, item: dict[str, Any]) -> float:
        memory_key = item.get("memory_key")
        if not memory_key:
            return 0.0

        query_tokens = set(_tokenize(query))
        if not query_tokens:
            return 0.0

        key_tokens = set(_tokenize(memory_key))
        if not key_tokens:
            return 0.0
        return 1.0 if query_tokens.issubset(key_tokens) else 0.0

    def _exact_phrase_match(self, query: str, item: dict[str, Any]) -> float:
        normalized_query = _normalized_text(query)
        if not normalized_query:
            return 0.0
        haystacks = [
            _normalized_text(item.get("text")),
            _normalized_text(item.get("preview")),
            _normalized_text(item.get("memory_key")),
            _normalized_text(item.get("memory_value")),
        ]
        return (
            1.0
            if any(
                normalized_query and normalized_query in haystack
                for haystack in haystacks
            )
            else 0.0
        )

    def _semantic_score(self, item: dict[str, Any]) -> float:
        try:
            similarity = float(item.get("similarity", 0) or 0)
        except (TypeError, ValueError):
            similarity = 0.0
        return max(0.0, min(similarity, 1.0))

    def _recency_scores(self, candidates: list[dict[str, Any]]) -> dict[str, float]:
        scored = sorted(
            [
                (
                    item.get("drawer_id") or f"candidate-{index}",
                    _timestamp_score(item.get("valid_from") or item.get("filed_at")),
                )
                for index, item in enumerate(candidates)
            ],
            key=lambda item: item[1],
            reverse=True,
        )
        if not scored:
            return {}
        if len(scored) == 1:
            return {scored[0][0]: 1.0}
        denominator = len(scored) - 1
        return {
            drawer_id: round(1 - (index / denominator), 3)
            for index, (drawer_id, _timestamp) in enumerate(scored)
        }

    def _candidate_value(self, item: dict[str, Any], key: str) -> Any:
        value = item.get(key)
        if value is not None:
            return value
        metadata = item.get("metadata")
        if isinstance(metadata, dict):
            return metadata.get(key)
        return None

    def _candidate_confidence(self, item: dict[str, Any]) -> float | None:
        confidence = _coerce_float(self._candidate_value(item, "confidence"))
        if confidence is None:
            return None
        return round(_clamp(confidence), 3)

    def _candidate_source_count(self, item: dict[str, Any]) -> int | None:
        source_count = _coerce_int(self._candidate_value(item, "source_count"))
        if source_count is None:
            return None
        return max(0, source_count)

    def _candidate_dedupe_key(self, item: dict[str, Any]) -> str:
        dedupe_hash = self._candidate_value(item, "dedupe_hash")
        if dedupe_hash:
            return f"dedupe:{dedupe_hash}"
        return f"drawer:{item.get('drawer_id')}"

    def _contract_rejection_reasons(self, item: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        contract = item.get("memory_contract")
        if not isinstance(contract, dict):
            return reasons

        if contract.get("valid_to") or contract.get("is_stale"):
            reasons.append("stale")
        if contract.get("superseded_by"):
            reasons.append("superseded")
        for reason in contract.get("reasons") or []:
            reasons.append(f"contract({reason})")
        return list(dict.fromkeys(reasons))

    def _reason_summary(self, reasons: list[str]) -> str:
        return ", ".join(reasons[:4])

    def _score_candidates(
        self,
        query: str,
        candidates: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        recency_scores = self._recency_scores(candidates)
        scored: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for index, item in enumerate(candidates):
            drawer_id = item.get("drawer_id") or f"candidate-{index}"
            keyword_score, keyword_tokens = self._keyword_overlap(query, item)
            memory_key_score = self._memory_key_match(query, item)
            exact_phrase_score = self._exact_phrase_match(query, item)
            semantic_score = self._semantic_score(item)
            search_tier = item.get("search_tier") or "filtered"
            tier_score = TIER_SCORE.get(search_tier, 0.5)
            recency_score = recency_scores.get(drawer_id, 0.0)
            base_total = (
                (keyword_score * 0.34)
                + (memory_key_score * 0.22)
                + (exact_phrase_score * 0.12)
                + (tier_score * 0.21)
                + (semantic_score * 0.105)
                + (recency_score * 0.005)
            )
            reasons: list[str] = []
            if keyword_tokens:
                reasons.append(f"keyword({', '.join(keyword_tokens)})")
            if memory_key_score > 0:
                reasons.append("memory_key")
            if exact_phrase_score > 0:
                reasons.append("exact_phrase")
            if semantic_score > 0:
                reasons.append("semantic")
            reasons.append(f"tier({search_tier})")

            confidence_score = self._candidate_confidence(item)
            confidence_bonus = 0.0
            if confidence_score is not None:
                reasons.append(f"confidence({confidence_score:.3f})")
                if confidence_score < LOW_CONFIDENCE_THRESHOLD:
                    reasons.append(
                        f"threshold(confidence<{LOW_CONFIDENCE_THRESHOLD:.2f})"
                    )
                else:
                    confidence_bonus = round(
                        (
                            (confidence_score - LOW_CONFIDENCE_THRESHOLD)
                            / (1 - LOW_CONFIDENCE_THRESHOLD)
                        )
                        * HIGH_CONFIDENCE_BONUS,
                        6,
                    )

            source_count_value = self._candidate_source_count(item)
            source_count_score = None
            source_count_bonus = 0.0
            if source_count_value is not None:
                source_count_score = round(
                    min(source_count_value, MAX_SOURCE_COUNT) / MAX_SOURCE_COUNT,
                    3,
                )
                reasons.append(f"source_count({source_count_value})")
                if source_count_value < LOW_SOURCE_COUNT_THRESHOLD:
                    reasons.append(
                        f"threshold(source_count<{LOW_SOURCE_COUNT_THRESHOLD})"
                    )
                else:
                    source_count_bonus = round(
                        (
                            (
                                min(source_count_value, MAX_SOURCE_COUNT)
                                - LOW_SOURCE_COUNT_THRESHOLD
                            )
                            / (MAX_SOURCE_COUNT - LOW_SOURCE_COUNT_THRESHOLD)
                        )
                        * HIGH_SOURCE_COUNT_BONUS,
                        6,
                    )

            low_overlap = (
                keyword_score < LOW_OVERLAP_THRESHOLD
                and memory_key_score <= 0
                and exact_phrase_score <= 0
            )
            semantic_only = (
                semantic_score > 0
                and keyword_score <= 0
                and memory_key_score <= 0
                and exact_phrase_score <= 0
            )

            penalty = 0.0
            if (
                confidence_score is not None
                and confidence_score < LOW_CONFIDENCE_THRESHOLD
            ):
                penalty += LOW_CONFIDENCE_PENALTY
            if (
                source_count_value is not None
                and source_count_value < LOW_SOURCE_COUNT_THRESHOLD
            ):
                penalty += LOW_SOURCE_COUNT_PENALTY
            if low_overlap:
                reasons.append("low_overlap")
                reasons.append(f"threshold(overlap<{LOW_OVERLAP_THRESHOLD:.2f})")
                penalty += LOW_OVERLAP_PENALTY
            if semantic_only:
                reasons.append("semantic_only")
                penalty += SEMANTIC_ONLY_PENALTY

            total_score = round(
                max(0.0, base_total + confidence_bonus + source_count_bonus - penalty),
                6,
            )
            retrieval_scores = {
                "keyword": round(keyword_score, 3),
                "memory_key": round(memory_key_score, 3),
                "exact_phrase": round(exact_phrase_score, 3),
                "semantic": round(semantic_score, 3),
                "tier": round(tier_score, 3),
                "recency": round(recency_score, 3),
                "overlap": round(keyword_score, 3),
                "confidence": confidence_score,
                "confidence_bonus": round(confidence_bonus, 6),
                "source_count": source_count_value,
                "source_count_score": source_count_score,
                "source_count_bonus": round(source_count_bonus, 6),
                "penalty": round(penalty, 6),
                "base_total": round(base_total, 6),
                "total": total_score,
            }

            rejection_reasons: list[str] = []
            if item.get("_contract_eligible") is False:
                rejection_reasons.extend(self._contract_rejection_reasons(item))
            if self._candidate_value(item, "valid_to") or self._candidate_value(
                item, "is_stale"
            ):
                rejection_reasons.append("stale")
            if self._candidate_value(item, "superseded_by"):
                rejection_reasons.append("superseded")
            rejection_reasons = list(dict.fromkeys(rejection_reasons))

            enriched = {
                **item,
                "reason_summary": self._reason_summary(reasons),
                "retrieval_reasons": reasons,
                "retrieval_scores": retrieval_scores,
                "_retrieval_index": index,
                "_retrieval_decision": "ranked",
            }
            if rejection_reasons:
                enriched["retrieval_reasons"] = rejection_reasons + reasons
                enriched["reason_summary"] = self._reason_summary(
                    enriched["retrieval_reasons"]
                )
                enriched["_retrieval_decision"] = "rejected"
                rejected.append(enriched)
                continue
            scored.append(enriched)

        ordered = sorted(
            scored,
            key=lambda item: (
                item["retrieval_scores"]["total"],
                item["retrieval_scores"]["keyword"],
                item["retrieval_scores"]["memory_key"],
                item["retrieval_scores"]["exact_phrase"],
                item["retrieval_scores"]["semantic"],
                item["retrieval_scores"]["tier"],
                item["retrieval_scores"]["recency"],
                -(item.get("_retrieval_index") or 0),
            ),
            reverse=True,
        )

        deduped: list[dict[str, Any]] = []
        seen_keys: dict[str, dict[str, Any]] = {}
        for item in ordered:
            dedupe_key = self._candidate_dedupe_key(item)
            if dedupe_key in seen_keys:
                winner = seen_keys[dedupe_key]
                duplicate_reasons = [
                    "duplicate",
                    f"duplicate_of({winner.get('drawer_id')})",
                    *item.get("retrieval_reasons", []),
                ]
                rejected.append(
                    {
                        **item,
                        "reason_summary": self._reason_summary(duplicate_reasons),
                        "retrieval_reasons": duplicate_reasons,
                        "_retrieval_decision": "rejected",
                    }
                )
                continue
            seen_keys[dedupe_key] = item
            deduped.append(item)
        return deduped, rejected

    def _ranked_trace(
        self,
        *,
        query: str,
        scored: list[dict[str, Any]],
        rejected: list[dict[str, Any]],
        limit: int,
    ) -> dict[str, Any]:
        returned_count = min(len(scored), limit)
        return {
            "query": query,
            "candidate_count": len(scored) + len(rejected),
            "returned_count": returned_count,
            "selected_count": returned_count,
            "truncated_count": max(0, len(scored) - limit),
            "chosen_results": [
                {
                    "id": item.get("drawer_id"),
                    "reason": item.get("reason_summary"),
                }
                for item in scored[:limit]
            ],
            "ranked_candidates": [
                {
                    "drawer_id": item.get("drawer_id"),
                    "search_tier": item.get("search_tier"),
                    "reason_summary": item.get("reason_summary"),
                    "reasons": item.get("retrieval_reasons", []),
                    "scores": item.get("retrieval_scores", {}),
                    "included": index < limit,
                    "decision": "selected" if index < limit else "truncated",
                }
                for index, item in enumerate(scored)
            ]
            + [
                {
                    "drawer_id": item.get("drawer_id"),
                    "search_tier": item.get("search_tier"),
                    "reason_summary": item.get("reason_summary"),
                    "reasons": item.get("retrieval_reasons", []),
                    "scores": item.get("retrieval_scores", {}),
                    "included": False,
                    "decision": item.get("_retrieval_decision") or "rejected",
                }
                for item in rejected
            ],
        }

    def rank_candidates(
        self,
        *,
        query: str,
        candidates: list[dict[str, Any]],
        limit: int,
        include_trace: bool = False,
    ) -> tuple[list[dict[str, Any]], int, int, dict[str, Any] | None]:
        normalized: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for item in candidates:
            drawer_id = item.get("drawer_id")
            if not drawer_id:
                continue
            if not item.get("text"):
                rejected.append(
                    {
                        **item,
                        "reason_summary": "missing_text",
                        "retrieval_reasons": ["missing_text"],
                        "retrieval_scores": {"total": 0.0, "penalty": 0.0},
                        "_retrieval_decision": "rejected",
                    }
                )
                continue
            normalized.append(item)

        scored, scored_rejections = self._score_candidates(query, normalized)
        rejected.extend(scored_rejections)
        total_count = len(scored)
        ranked = scored[:limit] if limit else []
        trace = (
            self._ranked_trace(
                query=query,
                scored=scored,
                rejected=rejected,
                limit=limit,
            )
            if include_trace
            else None
        )
        return ranked, total_count, max(0, total_count - len(ranked)), trace

    def _keyword_recall(
        self,
        *,
        query: str,
        tier_name: str,
        filters: dict[str, Any],
        limit: int,
    ) -> list[dict[str, Any]]:
        indexed = self.core.repository.keyword_query_drawers(
            query=query,
            limit=limit,
            **filters,
        )
        if indexed:
            return [
                {
                    **row,
                    "search_tier": tier_name,
                    "retrieval_source": row.get("retrieval_source") or "keyword",
                }
                for row in indexed
            ]

        rows = self.core.repository.query_drawers(
            query=None,
            limit=limit,
            **filters,
        )
        recalled: list[dict[str, Any]] = []
        for row in rows:
            keyword_score, _tokens = self._keyword_overlap(query, row)
            if not (
                keyword_score > 0
                or self._memory_key_match(query, row) > 0
                or self._exact_phrase_match(query, row) > 0
            ):
                continue
            recalled.append(
                {
                    **row,
                    "search_tier": tier_name,
                    "retrieval_source": "keyword",
                }
            )
        return recalled

    def search_context(
        self,
        *,
        query: str,
        directory: str,
        wing: str,
        session_id: str | None = None,
        include_trace: bool = False,
    ) -> tuple[list[dict[str, Any]], int, int, dict[str, Any] | None]:
        limit = max(1, int(self.core.config.search_limit or 0))
        candidate_limit = self._candidate_limit(limit)
        keyword_limit = self._keyword_candidate_limit(limit)
        tiers = []
        if session_id:
            tiers.append(("session", {"session_id": session_id}))
        tiers.append(("directory", {"directory": directory}))
        tiers.append(("wing", {"wing": wing}))
        tiers.append(("global", {"wing": self.core.global_memory_wing}))

        candidates: list[dict[str, Any]] = []
        for tier_name, filters in tiers:
            rows = self.core.repository.query_drawers(
                query=query,
                limit=candidate_limit,
                current_only=True,
                **filters,
            )
            for row in rows:
                contracted = self._apply_context_contract(
                    {**row, "search_tier": tier_name},
                    directory=directory,
                    wing=wing,
                )
                if contracted is not None:
                    candidates.append(contracted)
            for row in self._keyword_recall(
                query=query,
                tier_name=tier_name,
                filters={**filters, "current_only": True},
                limit=keyword_limit,
            ):
                contracted = self._apply_context_contract(
                    row,
                    directory=directory,
                    wing=wing,
                )
                if contracted is not None:
                    candidates.append(contracted)

        return self.rank_candidates(
            query=query,
            candidates=candidates,
            limit=limit,
            include_trace=include_trace,
        )

    def search_drawers(
        self,
        *,
        query: str,
        limit: int,
        wing: str | None = None,
        memory_tier: str | None = None,
        current_only: bool = False,
        historical_only: bool = False,
        room: str | None = None,
        include_trace: bool = False,
    ) -> tuple[list[dict[str, Any]], int, int, dict[str, Any] | None]:
        candidate_limit = self._candidate_limit(limit)
        keyword_limit = self._keyword_candidate_limit(limit)
        rows = self.core.repository.query_drawers(
            query=query,
            wing=wing,
            memory_tier=memory_tier,
            current_only=current_only,
            historical_only=historical_only,
            room=room,
            limit=candidate_limit,
        )
        candidates = [
            {**row, "search_tier": row.get("search_tier") or "filtered"} for row in rows
        ]
        candidates.extend(
            self._keyword_recall(
                query=query,
                tier_name="filtered",
                filters={
                    "wing": wing,
                    "memory_tier": memory_tier,
                    "current_only": current_only,
                    "historical_only": historical_only,
                    "room": room,
                },
                limit=keyword_limit,
            )
        )
        return self.rank_candidates(
            query=query,
            candidates=candidates,
            limit=limit,
            include_trace=include_trace,
        )


__all__ = ["ContextRetrievalService"]
