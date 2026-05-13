from __future__ import annotations

import sys
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


PENALTY_TEST_QUERY = "git commit confirmation approval workflow policy"


def _retrieval_row(
    drawer_id: str,
    *,
    text: str,
    valid_from: str,
    similarity: float,
    preview: str | None = None,
    memory_key: str | None = None,
    memory_value: str | None = None,
    confidence: float | None = None,
    source_count: int | None = None,
    dedupe_hash: str | None = None,
    valid_to: str | None = None,
    superseded_by: str | None = None,
) -> dict[str, object]:
    metadata: dict[str, object] = {}
    if confidence is not None:
        metadata["confidence"] = confidence
    if source_count is not None:
        metadata["source_count"] = source_count
    if dedupe_hash is not None:
        metadata["dedupe_hash"] = dedupe_hash
    if valid_to is not None:
        metadata["valid_to"] = valid_to
    if superseded_by is not None:
        metadata["superseded_by"] = superseded_by
    return {
        "drawer_id": drawer_id,
        "text": text,
        "preview": preview or text,
        "wing": "opencode",
        "room": "opencode-session",
        "directory": "/home/mechrevo/.config/opencode",
        "source_file": "session:ses_task_6_penalties",
        "session_id": "ses_task_6_penalties",
        "message_id": f"msg_{drawer_id}",
        "role": "assistant",
        "memory_tier": "project_memory",
        "memory_key": memory_key,
        "memory_value": memory_value,
        "dedupe_hash": dedupe_hash,
        "confidence": confidence,
        "source_count": source_count,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "superseded_by": superseded_by,
        "filed_at": valid_from,
        "similarity": similarity,
        "distance": round(max(0.0, 1 - similarity), 3),
        "metadata": metadata,
    }


def _build_core(*, backend, prefix: str, search_limit: int = 5):
    from evomemory.context.bridge import BridgeConfig, BridgeCore

    temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
    return BridgeCore(
        BridgeConfig(state_path=temp_dir / "state.sqlite3", search_limit=search_limit),
        backend=backend,
    )


class HybridRetrievalBackend:
    def query_drawers(
        self,
        *,
        query=None,
        wing=None,
        directory=None,
        memory_tier=None,
        current_only=False,
        historical_only=False,
        room=None,
        session_id=None,
        role=None,
        source_file=None,
        limit=20,
        offset=0,
    ):
        if query is None:
            return []

        if session_id is not None or directory is not None:
            return []

        if wing != "opencode" or not current_only:
            return []

        rows = [
            {
                "drawer_id": "drawer_noise_1",
                "text": "Assistant: I like the state machine approach for this refactor.",
                "preview": "Assistant: I like the state machine approach for this refactor.",
                "wing": "opencode",
                "room": "opencode-session",
                "directory": "/home/mechrevo/.config/opencode",
                "source_file": "session:ses_hybrid",
                "session_id": "ses_hybrid",
                "message_id": "msg_noise_1",
                "role": "assistant",
                "memory_tier": "working_session",
                "memory_key": None,
                "memory_value": None,
                "dedupe_hash": None,
                "valid_from": "2026-04-01T10:00:00+00:00",
                "valid_to": None,
                "working_summary": False,
                "filed_at": "2026-04-01T10:00:00+00:00",
                "similarity": 0.96,
                "distance": 0.04,
                "metadata": {},
            },
            {
                "drawer_id": "drawer_noise_2",
                "text": "Assistant: We should update the parser before touching the cache.",
                "preview": "Assistant: We should update the parser before touching the cache.",
                "wing": "opencode",
                "room": "opencode-session",
                "directory": "/home/mechrevo/.config/opencode",
                "source_file": "session:ses_hybrid",
                "session_id": "ses_hybrid",
                "message_id": "msg_noise_2",
                "role": "assistant",
                "memory_tier": "working_session",
                "memory_key": None,
                "memory_value": None,
                "dedupe_hash": None,
                "valid_from": "2026-04-01T10:01:00+00:00",
                "valid_to": None,
                "working_summary": False,
                "filed_at": "2026-04-01T10:01:00+00:00",
                "similarity": 0.91,
                "distance": 0.09,
                "metadata": {},
            },
            {
                "drawer_id": "drawer_keyword",
                "text": "Assistant: 不要自动提交 git commit，先确认再说。",
                "preview": "Assistant: 不要自动提交 git commit，先确认再说。",
                "wing": "opencode",
                "room": "opencode-session",
                "directory": "/home/mechrevo/.config/opencode",
                "source_file": "session:ses_hybrid",
                "session_id": "ses_hybrid",
                "message_id": "msg_keyword",
                "role": "assistant",
                "memory_tier": "project_memory",
                "memory_key": "git_commit_behavior",
                "memory_value": "disabled",
                "dedupe_hash": None,
                "valid_from": "2026-04-01T10:02:00+00:00",
                "valid_to": None,
                "working_summary": False,
                "filed_at": "2026-04-01T10:02:00+00:00",
                "similarity": 0.12,
                "distance": 0.88,
                "metadata": {},
            },
        ]
        return rows[offset : offset + limit]

    def get_session_messages(self, **kwargs):
        return []

    def save_entry(self, **kwargs):
        raise AssertionError("save_entry should not be called in retrieval tests")

    def invalidate_memory_conflicts(self, **kwargs):
        return 0

    def invalidate_drawers(self, **kwargs):
        return 0

    def status(self):
        return {"total_drawers": 0, "palace_path": "/tmp/palace"}

    def memory_stats(self):
        return {}

    def list_wings(self):
        return {}

    def list_rooms(self, wing=None):
        return {}

    def get_taxonomy(self):
        return {}

    def list_drawers(self, **kwargs):
        return self.query_drawers(**kwargs)

    def get_drawer(self, drawer_id):
        return None

    def list_sessions(self, **kwargs):
        return []

    def kg_query(self, entity, as_of=None, direction="both"):
        return {
            "entity": entity,
            "facts": [],
            "count": 0,
            "as_of": as_of,
            "direction": direction,
        }


class KeywordRecallBackend(HybridRetrievalBackend):
    def query_drawers(
        self,
        *,
        query=None,
        wing=None,
        directory=None,
        memory_tier=None,
        current_only=False,
        historical_only=False,
        room=None,
        session_id=None,
        role=None,
        source_file=None,
        limit=20,
        offset=0,
    ):
        if query is not None:
            return [
                {
                    "drawer_id": "drawer_semantic_noise",
                    "text": "Assistant: Parser cache refactor notes.",
                    "preview": "Assistant: Parser cache refactor notes.",
                    "wing": "opencode",
                    "room": "opencode-session",
                    "directory": "/home/mechrevo/.config/opencode",
                    "source_file": "session:ses_noise",
                    "session_id": "ses_noise",
                    "message_id": "msg_noise",
                    "role": "assistant",
                    "memory_tier": "working_session",
                    "memory_key": None,
                    "memory_value": None,
                    "valid_from": "2026-04-01T10:00:00+00:00",
                    "valid_to": None,
                    "filed_at": "2026-04-01T10:00:00+00:00",
                    "similarity": 0.95,
                    "distance": 0.05,
                    "metadata": {},
                }
            ][:limit]

        if wing != "opencode" or not current_only:
            return []
        return [
            {
                "drawer_id": "drawer_keyword_recall",
                "text": "Assistant: Project rule is do not auto run git commit without confirmation.",
                "preview": "Assistant: Project rule is do not auto run git commit without confirmation.",
                "wing": "opencode",
                "room": "opencode-session",
                "directory": "/home/mechrevo/.config/opencode",
                "source_file": "session:ses_keyword_recall",
                "session_id": "ses_keyword_recall",
                "message_id": "msg_keyword_recall",
                "role": "assistant",
                "memory_tier": "project_memory",
                "memory_key": "git_commit_behavior",
                "memory_value": "disabled",
                "valid_from": "2026-04-01T11:00:00+00:00",
                "valid_to": None,
                "filed_at": "2026-04-01T11:00:00+00:00",
                "similarity": 0.0,
                "distance": None,
                "metadata": {},
            }
        ][:limit]


class PenaltyRetrievalBackend(HybridRetrievalBackend):
    def query_drawers(
        self,
        *,
        query=None,
        wing=None,
        directory=None,
        memory_tier=None,
        current_only=False,
        historical_only=False,
        room=None,
        session_id=None,
        role=None,
        source_file=None,
        limit=20,
        offset=0,
    ):
        if query is None:
            return []

        if wing != "opencode" or not current_only:
            return []

        if session_id is not None or directory is not None:
            return []

        rows = [
            _retrieval_row(
                "drawer_primary",
                text="Assistant: git commit confirmation approval workflow policy is to ask before committing.",
                preview="git commit confirmation approval workflow policy",
                memory_key="git_commit_confirmation_approval_workflow_policy",
                memory_value="ask_before_commit",
                valid_from="2026-04-01T10:08:00+00:00",
                similarity=0.68,
                confidence=0.93,
                source_count=4,
                dedupe_hash="commit-confirmation-policy",
            ),
            _retrieval_row(
                "drawer_supporting",
                text="Assistant: The policy requires git commit approval and confirmation before repository changes.",
                valid_from="2026-04-01T10:07:00+00:00",
                similarity=0.41,
                confidence=0.7,
                source_count=2,
            ),
            _retrieval_row(
                "drawer_penalized",
                text="Assistant: The git commit policy asks for confirmation and approval from the user.",
                valid_from="2026-04-01T10:06:00+00:00",
                similarity=0.28,
                confidence=0.2,
                source_count=1,
            ),
            _retrieval_row(
                "drawer_low_overlap",
                text="Assistant: Git cleanup note for background tasks only.",
                valid_from="2026-04-01T10:05:00+00:00",
                similarity=0.4,
                confidence=0.8,
                source_count=3,
            ),
            _retrieval_row(
                "drawer_semantic_only",
                text="Assistant: Repository automation preference for future work.",
                valid_from="2026-04-01T10:04:00+00:00",
                similarity=0.99,
                confidence=0.8,
                source_count=3,
            ),
            _retrieval_row(
                "drawer_stale",
                text="Assistant: Old git commit confirmation approval workflow policy.",
                valid_from="2026-04-01T10:03:00+00:00",
                similarity=0.62,
                confidence=0.8,
                source_count=3,
                valid_to="2026-04-02T00:00:00+00:00",
            ),
            _retrieval_row(
                "drawer_superseded",
                text="Assistant: Superseded git commit confirmation approval workflow policy.",
                valid_from="2026-04-01T10:02:00+00:00",
                similarity=0.57,
                confidence=0.75,
                source_count=3,
                superseded_by="drawer_primary",
            ),
            _retrieval_row(
                "drawer_duplicate",
                text="Assistant: Duplicate git commit confirmation approval workflow policy note.",
                valid_from="2026-04-01T10:01:00+00:00",
                similarity=0.52,
                confidence=0.6,
                source_count=2,
                dedupe_hash="commit-confirmation-policy",
            ),
        ]
        return rows[offset : offset + limit]


def test_search_context_prioritizes_keyword_overlap_over_higher_similarity_noise():
    from evomemory.context.bridge import BridgeConfig, BridgeCore

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-hybrid-rank-"))
    core = BridgeCore(
        BridgeConfig(state_path=temp_dir / "state.sqlite3"),
        backend=HybridRetrievalBackend(),
    )

    result = core.search_context(
        "git commit",
        "/home/mechrevo/.config/opencode",
        session_id="ses_hybrid",
        include_trace=True,
    )

    assert result["results"][0]["drawer_id"] == "drawer_keyword"
    assert {item["drawer_id"] for item in result["results"][:3]} == {
        "drawer_keyword",
        "drawer_noise_1",
        "drawer_noise_2",
    }


def test_search_context_exposes_retrieval_trace_for_ranked_candidates():
    from evomemory.context.bridge import BridgeConfig, BridgeCore

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-hybrid-trace-"))
    core = BridgeCore(
        BridgeConfig(state_path=temp_dir / "state.sqlite3"),
        backend=HybridRetrievalBackend(),
    )

    result = core.search_context(
        "git commit",
        "/home/mechrevo/.config/opencode",
        session_id="ses_hybrid",
        include_trace=True,
    )

    trace = result.get("retrieval_trace")
    assert trace is not None
    assert trace["query"] == "git commit"
    assert trace["ranked_candidates"][0]["drawer_id"] == "drawer_keyword"
    assert any(
        reason.startswith("keyword(")
        for reason in trace["ranked_candidates"][0]["reasons"]
    )


def test_search_context_recalls_keyword_hits_missed_by_semantic_query():
    core = _build_core(
        backend=KeywordRecallBackend(),
        prefix="evomemory-keyword-recall-",
    )

    result = core.search_context(
        "git commit",
        "/home/mechrevo/.config/opencode",
        session_id="ses_keyword_recall",
        include_trace=True,
    )

    assert result["results"][0]["drawer_id"] == "drawer_keyword_recall"
    assert result["results"][0]["retrieval_source"] == "keyword"
    assert (
        result["retrieval_trace"]["ranked_candidates"][0]["drawer_id"]
        == "drawer_keyword_recall"
    )


def test_search_context_penalties_demote_noise_and_exclude_rejected_candidates():
    core = _build_core(
        backend=PenaltyRetrievalBackend(),
        prefix="evomemory-penalty-rank-",
        search_limit=3,
    )

    result = core.search_context(
        PENALTY_TEST_QUERY,
        "/home/mechrevo/.config/opencode",
        session_id="ses_task_6_penalties",
        include_trace=True,
    )

    assert [item["drawer_id"] for item in result["results"]] == [
        "drawer_primary",
        "drawer_supporting",
        "drawer_penalized",
    ]

    trace = result["retrieval_trace"]
    ranked = trace["ranked_candidates"]
    assert trace["candidate_count"] == 8
    assert trace["selected_count"] == 3
    assert [item["drawer_id"] for item in ranked[:5]] == [
        "drawer_primary",
        "drawer_supporting",
        "drawer_penalized",
        "drawer_low_overlap",
        "drawer_semantic_only",
    ]

    ranked_by_id = {item["drawer_id"]: item for item in ranked}
    assert ranked_by_id["drawer_low_overlap"]["included"] is False
    assert ranked_by_id["drawer_low_overlap"]["decision"] == "truncated"
    assert ranked_by_id["drawer_semantic_only"]["included"] is False
    assert ranked_by_id["drawer_semantic_only"]["decision"] == "truncated"
    assert ranked_by_id["drawer_stale"]["included"] is False
    assert ranked_by_id["drawer_stale"]["decision"] == "rejected"
    assert ranked_by_id["drawer_superseded"]["included"] is False
    assert ranked_by_id["drawer_superseded"]["decision"] == "rejected"
    assert ranked_by_id["drawer_duplicate"]["included"] is False
    assert ranked_by_id["drawer_duplicate"]["decision"] == "rejected"

    assert (
        ranked_by_id["drawer_primary"]["scores"]["total"]
        > ranked_by_id["drawer_penalized"]["scores"]["total"]
        > ranked_by_id["drawer_low_overlap"]["scores"]["total"]
        > ranked_by_id["drawer_semantic_only"]["scores"]["total"]
    )
    assert ranked_by_id["drawer_penalized"]["scores"]["penalty"] == 0.075
    assert ranked_by_id["drawer_low_overlap"]["scores"]["penalty"] == 0.09
    assert ranked_by_id["drawer_semantic_only"]["scores"]["penalty"] == 0.16


def test_search_context_trace_captures_penalty_and_rejection_reasons():
    core = _build_core(
        backend=PenaltyRetrievalBackend(),
        prefix="evomemory-penalty-trace-",
        search_limit=3,
    )

    result = core.search_context(
        PENALTY_TEST_QUERY,
        "/home/mechrevo/.config/opencode",
        session_id="ses_task_6_penalties",
        include_trace=True,
    )

    ranked_by_id = {
        item["drawer_id"]: item
        for item in result["retrieval_trace"]["ranked_candidates"]
    }

    penalized_reasons = ranked_by_id["drawer_penalized"]["reasons"]
    assert any(
        reason.startswith("threshold(confidence<") for reason in penalized_reasons
    )
    assert any(reason.startswith("source_count(") for reason in penalized_reasons)
    assert any(
        reason.startswith("threshold(source_count<") for reason in penalized_reasons
    )

    low_overlap_reasons = ranked_by_id["drawer_low_overlap"]["reasons"]
    assert "low_overlap" in low_overlap_reasons
    assert any(
        reason.startswith("threshold(overlap<") for reason in low_overlap_reasons
    )

    semantic_reasons = ranked_by_id["drawer_semantic_only"]["reasons"]
    assert "low_overlap" in semantic_reasons
    assert "semantic_only" in semantic_reasons

    stale_reasons = ranked_by_id["drawer_stale"]["reasons"]
    assert stale_reasons[0] == "stale"

    superseded_reasons = ranked_by_id["drawer_superseded"]["reasons"]
    assert superseded_reasons[0] == "superseded"

    duplicate_reasons = ranked_by_id["drawer_duplicate"]["reasons"]
    assert duplicate_reasons[0] == "duplicate"
    assert "duplicate_of(drawer_primary)" in duplicate_reasons
