from __future__ import annotations

import sys
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


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
        return {"entity": entity, "facts": [], "count": 0, "as_of": as_of, "direction": direction}


def test_search_context_prioritizes_keyword_overlap_over_higher_similarity_noise():
    from evomemory.context.bridge import BridgeConfig, BridgeCore

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-hybrid-rank-"))
    core = BridgeCore(BridgeConfig(state_path=temp_dir / "state.sqlite3"), backend=HybridRetrievalBackend())

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
    core = BridgeCore(BridgeConfig(state_path=temp_dir / "state.sqlite3"), backend=HybridRetrievalBackend())

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
