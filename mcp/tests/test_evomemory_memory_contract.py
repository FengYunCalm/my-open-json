from __future__ import annotations

import sys
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evomemory.context.bridge import BridgeConfig, BridgeCore
from evomemory.domain.memory_policy import (
    MEMORY_CONTRACT_STATUS_DOWNGRADED,
    MEMORY_CONTRACT_STATUS_LEGACY,
    MEMORY_CONTRACT_STATUS_REJECTED,
    MEMORY_CONTRACT_STATUS_TRUSTED,
    assess_memory_contract,
)


CURRENT_DIRECTORY = "/home/mechrevo/.config/opencode"
FOREIGN_DIRECTORY = "/home/mechrevo/projects/project-beta"


def make_row(
    drawer_id: str,
    *,
    text: str = "Assistant: do not auto run git commit without confirmation.",
    wing: str = "opencode",
    directory: str | None = CURRENT_DIRECTORY,
    source_file: str | None = "session:ses_alpha",
    session_id: str | None = "ses_alpha",
    message_id: str | None = "msg_alpha",
    memory_tier: str = "project_memory",
    memory_key: str | None = "git_commit_behavior",
    memory_value: str | None = "disabled",
    valid_from: str | None = "2026-05-12T00:00:00+00:00",
    filed_at: str | None = None,
    valid_to: str | None = None,
    confidence: float | None = None,
    source_count: int | None = None,
    superseded_by: str | None = None,
    conflict_reason: str | None = None,
    conflict_drawer_ids: list[str] | None = None,
    demoted_at: str | None = None,
) -> dict:
    return {
        "drawer_id": drawer_id,
        "text": text,
        "preview": text,
        "wing": wing,
        "room": "opencode-session",
        "directory": directory,
        "source_file": source_file,
        "session_id": session_id,
        "message_id": message_id,
        "role": "assistant",
        "memory_tier": memory_tier,
        "memory_key": memory_key,
        "memory_value": memory_value,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "filed_at": filed_at or valid_from,
        "confidence": confidence,
        "source_count": source_count,
        "superseded_by": superseded_by,
        "conflict_reason": conflict_reason,
        "conflict_drawer_ids": conflict_drawer_ids or [],
        "demoted_at": demoted_at,
        "similarity": 0.82,
        "distance": 0.18,
        "metadata": {},
    }


class MemoryContractBackend:
    def __init__(self, rows: list[dict]):
        self.rows = list(rows)

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
        rows = list(self.rows)
        if wing is not None:
            rows = [row for row in rows if row.get("wing") == wing]
        if directory is not None:
            rows = [row for row in rows if row.get("directory") == directory]
        if memory_tier is not None:
            rows = [row for row in rows if row.get("memory_tier") == memory_tier]
        if current_only:
            rows = [row for row in rows if not row.get("valid_to")]
        elif historical_only:
            rows = [row for row in rows if row.get("valid_to")]
        if room is not None:
            rows = [row for row in rows if row.get("room") == room]
        if session_id is not None:
            rows = [row for row in rows if row.get("session_id") == session_id]
        if role is not None:
            rows = [row for row in rows if row.get("role") == role]
        if source_file is not None:
            rows = [row for row in rows if row.get("source_file") == source_file]
        if query is not None:
            lowered = query.lower()
            rows = [
                row
                for row in rows
                if lowered in (row.get("text") or "").lower()
                or lowered in (row.get("preview") or "").lower()
                or lowered in (row.get("memory_key") or "").lower()
                or lowered in (row.get("memory_value") or "").lower()
            ]
        return rows[offset : offset + limit]

    def get_session_messages(self, **kwargs):
        return []

    def save_entry(self, **kwargs):
        raise AssertionError("save_entry should not be called in contract tests")

    def invalidate_memory_conflicts(self, **kwargs):
        return 0

    def invalidate_drawers(self, **kwargs):
        return 0

    def status(self):
        return {"total_drawers": len(self.rows), "palace_path": "/tmp/palace"}

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
        for row in self.rows:
            if row.get("drawer_id") == drawer_id:
                return row
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


def make_core(rows: list[dict]) -> BridgeCore:
    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-memory-contract-"))
    return BridgeCore(
        BridgeConfig(
            search_limit=10,
            core_memory_limit=0,
            state_path=temp_dir / "state.json",
            wing_config_path=temp_dir / "wing_config.json",
        ),
        backend=MemoryContractBackend(rows),
    )


def test_same_directory_project_memory_is_trusted_long_term():
    contract = assess_memory_contract(
        make_row("drawer_same_project"),
        current_directory=CURRENT_DIRECTORY,
        current_wing="opencode",
    )

    assert contract["status"] == MEMORY_CONTRACT_STATUS_TRUSTED
    assert contract["eligible_for_context"] is True
    assert contract["namespace"]["directory"] == CURRENT_DIRECTORY
    assert contract["namespace"]["wing"] == "opencode"
    assert contract["provenance"]["message_id"] == "msg_alpha"
    assert contract["confidence"] == 0.0
    assert contract["source_count"] == 1


def test_search_context_excludes_foreign_project_memory_from_wing_and_global_fallbacks():
    core = make_core(
        [
            make_row(
                "drawer_same_project",
                text="Assistant: do not auto run git commit without confirmation.",
                session_id="ses_current",
                message_id="msg_current",
                source_file="session:ses_current",
            ),
            make_row(
                "drawer_foreign_wing",
                text="Assistant: foreign project says do not auto run git commit.",
                directory=FOREIGN_DIRECTORY,
                session_id="ses_foreign_wing",
                message_id="msg_foreign_wing",
                source_file="session:ses_foreign_wing",
            ),
            make_row(
                "drawer_foreign_global",
                text="Assistant: global fallback says do not auto run git commit.",
                wing="global-memory",
                directory="/home/mechrevo/shared/project-gamma",
                session_id="ses_foreign_global",
                message_id="msg_foreign_global",
                source_file="session:ses_foreign_global",
            ),
        ]
    )

    result = core.search_context(
        "git commit",
        CURRENT_DIRECTORY,
        session_id="ses_current",
    )

    assert [item["drawer_id"] for item in result["results"]] == ["drawer_same_project"]
    assert result["context_total_count"] == 1
    assert "drawer_foreign_wing" not in [
        item["drawer_id"] for item in result["results"]
    ]
    assert "drawer_foreign_global" not in [
        item["drawer_id"] for item in result["results"]
    ]


def test_legacy_long_term_missing_provenance_is_safe_but_not_trusted():
    contract = assess_memory_contract(
        make_row(
            "drawer_legacy_preference",
            text="User: 以后都用中文回复。",
            memory_tier="user_preference",
            memory_key="response_language",
            memory_value="zh-cn",
            source_file=None,
            session_id=None,
            message_id=None,
        ),
        current_directory=CURRENT_DIRECTORY,
        current_wing="opencode",
    )

    assert contract["status"] == MEMORY_CONTRACT_STATUS_LEGACY
    assert contract["eligible_for_context"] is False
    assert contract["namespace"]["wing"] == "opencode"
    assert contract["namespace"]["source"] is None
    assert contract["confidence"] == 0.0
    assert contract["source_count"] == 0
    assert contract["defaults_applied"] == ["confidence", "source_count"]


def test_missing_namespace_and_provenance_is_rejected_for_long_term_memory():
    contract = assess_memory_contract(
        make_row(
            "drawer_missing_namespace",
            directory=None,
            wing=None,
            source_file=None,
            session_id=None,
            message_id=None,
            valid_from=None,
            filed_at=None,
        ),
        current_directory=CURRENT_DIRECTORY,
        current_wing="opencode",
    )

    assert contract["status"] == MEMORY_CONTRACT_STATUS_REJECTED
    assert contract["eligible_for_context"] is False
    assert "missing_directory" in contract["reasons"]


def test_supersession_and_conflict_metadata_are_preserved():
    contract = assess_memory_contract(
        make_row(
            "drawer_superseded",
            superseded_by="drawer_newer",
            conflict_reason="conflicting_memory_value",
            conflict_drawer_ids=["drawer_old_1", "drawer_old_2"],
            demoted_at="2026-05-12T01:00:00+00:00",
        ),
        current_directory=CURRENT_DIRECTORY,
        current_wing="opencode",
    )

    assert contract["status"] == MEMORY_CONTRACT_STATUS_DOWNGRADED
    assert contract["superseded_by"] == "drawer_newer"
    assert contract["conflict"]["conflict_reason"] == "conflicting_memory_value"
    assert contract["conflict"]["conflict_drawer_ids"] == [
        "drawer_old_1",
        "drawer_old_2",
    ]
    assert contract["conflict"]["demoted_at"] == "2026-05-12T01:00:00+00:00"
