from __future__ import annotations

from datetime import datetime
import re
from typing import Any


TOKEN_PATTERN = re.compile(r"[a-z0-9_]+|[\u4e00-\u9fff]+", re.IGNORECASE)
TIER_SCORE = {
    "session": 1.0,
    "directory": 0.8,
    "wing": 0.6,
    "global": 0.4,
    "filtered": 0.5,
}


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


class ContextRetrievalService:
    def __init__(self, core: Any):
        self.core = core

    def _candidate_limit(self, limit: int) -> int:
        return max(limit * 8, 20)

    def _keyword_overlap(self, query: str, item: dict[str, Any]) -> tuple[float, list[str]]:
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
        return 1.0 if any(normalized_query and normalized_query in haystack for haystack in haystacks) else 0.0

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

    def _reason_summary(
        self,
        *,
        keyword_tokens: list[str],
        memory_key_score: float,
        exact_phrase_score: float,
        semantic_score: float,
        search_tier: str,
    ) -> tuple[str, list[str]]:
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
        return ", ".join(reasons[:4]), reasons

    def _score_candidates(
        self,
        query: str,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        recency_scores = self._recency_scores(candidates)
        scored: list[dict[str, Any]] = []
        for index, item in enumerate(candidates):
            drawer_id = item.get("drawer_id") or f"candidate-{index}"
            keyword_score, keyword_tokens = self._keyword_overlap(query, item)
            memory_key_score = self._memory_key_match(query, item)
            exact_phrase_score = self._exact_phrase_match(query, item)
            semantic_score = self._semantic_score(item)
            search_tier = item.get("search_tier") or "filtered"
            tier_score = TIER_SCORE.get(search_tier, 0.5)
            recency_score = recency_scores.get(drawer_id, 0.0)
            total_score = round(
                (keyword_score * 0.34)
                + (memory_key_score * 0.22)
                + (exact_phrase_score * 0.12)
                + (tier_score * 0.21)
                + (semantic_score * 0.105)
                + (recency_score * 0.005),
                6,
            )
            reason_summary, reasons = self._reason_summary(
                keyword_tokens=keyword_tokens,
                memory_key_score=memory_key_score,
                exact_phrase_score=exact_phrase_score,
                semantic_score=semantic_score,
                search_tier=search_tier,
            )
            scored.append(
                {
                    **item,
                    "reason_summary": reason_summary,
                    "retrieval_reasons": reasons,
                    "retrieval_scores": {
                        "keyword": round(keyword_score, 3),
                        "memory_key": round(memory_key_score, 3),
                        "exact_phrase": round(exact_phrase_score, 3),
                        "semantic": round(semantic_score, 3),
                        "tier": round(tier_score, 3),
                        "recency": round(recency_score, 3),
                        "total": total_score,
                    },
                    "_retrieval_index": index,
                }
            )
        return sorted(
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

    def _ranked_trace(
        self,
        *,
        query: str,
        scored: list[dict[str, Any]],
        limit: int,
    ) -> dict[str, Any]:
        return {
            "query": query,
            "candidate_count": len(scored),
            "returned_count": min(len(scored), limit),
            "truncated_count": max(0, len(scored) - limit),
            "ranked_candidates": [
                {
                    "drawer_id": item.get("drawer_id"),
                    "search_tier": item.get("search_tier"),
                    "reason_summary": item.get("reason_summary"),
                    "reasons": item.get("retrieval_reasons", []),
                    "scores": item.get("retrieval_scores", {}),
                    "included": index < limit,
                }
                for index, item in enumerate(scored)
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
        deduped: list[dict[str, Any]] = []
        seen = set()
        for item in candidates:
            drawer_id = item.get("drawer_id")
            if not drawer_id or drawer_id in seen:
                continue
            if not item.get("text"):
                continue
            seen.add(drawer_id)
            deduped.append(item)

        scored = self._score_candidates(query, deduped)
        total_count = len(scored)
        ranked = scored[:limit] if limit else []
        trace = (
            self._ranked_trace(query=query, scored=scored, limit=limit)
            if include_trace
            else None
        )
        return ranked, total_count, max(0, total_count - len(ranked)), trace

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
                candidates.append({**row, "search_tier": tier_name})

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
        rows = self.core.repository.query_drawers(
            query=query,
            wing=wing,
            memory_tier=memory_tier,
            current_only=current_only,
            historical_only=historical_only,
            room=room,
            limit=candidate_limit,
        )
        candidates = [{**row, "search_tier": row.get("search_tier") or "filtered"} for row in rows]
        return self.rank_candidates(
            query=query,
            candidates=candidates,
            limit=limit,
            include_trace=include_trace,
        )


__all__ = ["ContextRetrievalService"]
