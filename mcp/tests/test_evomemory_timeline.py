from __future__ import annotations

import sys
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class NoopBackend:
    pass


def test_query_beliefs_supports_as_of_point_in_time_lookup():
    from evomemory.context.bridge import BridgeConfig, BridgeCore

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-belief-asof-"))
    core = BridgeCore(BridgeConfig(state_path=temp_dir / "state.sqlite3"), backend=NoopBackend())

    core.promoter.promote_saved_memory(
        scope="project",
        memory_tier="project_memory",
        memory_key="git_commit_behavior",
        memory_value="disabled",
        source_session="ses_asof",
        source_message_id="msg_asof_1",
        source_record_id="drawer_asof_1",
        valid_from="2026-04-01T10:00:00+00:00",
    )
    core.promoter.promote_saved_memory(
        scope="project",
        memory_tier="project_memory",
        memory_key="git_commit_behavior",
        memory_value="confirm_first",
        source_session="ses_asof",
        source_message_id="msg_asof_2",
        source_record_id="drawer_asof_2",
        valid_from="2026-04-02T10:00:00+00:00",
    )

    earlier = core.evomemory_query_beliefs(
        scope="project",
        key="git_commit_behavior",
        as_of="2026-04-01T18:00:00+00:00",
    )
    later = core.evomemory_query_beliefs(
        scope="project",
        key="git_commit_behavior",
        as_of="2026-04-02T18:00:00+00:00",
    )

    assert earlier["count"] == 1
    assert earlier["facts"][0]["value"] == "disabled"
    assert later["count"] == 1
    assert later["facts"][0]["value"] == "confirm_first"


def test_query_timeline_returns_belief_history_and_related_governance_assets():
    from evomemory.context.bridge import BridgeConfig, BridgeCore

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-timeline-"))
    core = BridgeCore(BridgeConfig(state_path=temp_dir / "state.sqlite3"), backend=NoopBackend())

    core.promoter.promote_saved_memory(
        scope="project",
        memory_tier="project_memory",
        memory_key="git_commit_behavior",
        memory_value="disabled",
        source_session="ses_timeline",
        source_message_id="msg_timeline_1",
        source_record_id="drawer_timeline_1",
        valid_from="2026-04-01T10:00:00+00:00",
    )
    core.promoter.promote_saved_memory(
        scope="project",
        memory_tier="project_memory",
        memory_key="git_commit_behavior",
        memory_value="confirm_first",
        source_session="ses_timeline",
        source_message_id="msg_timeline_2",
        source_record_id="drawer_timeline_2",
        valid_from="2026-04-02T10:00:00+00:00",
    )

    result = core.evomemory_query_timeline(
        scope="project",
        key="git_commit_behavior",
        as_of="2026-04-02T18:00:00+00:00",
        limit=20,
    )

    assert result["scope"] == "project"
    assert result["key"] == "git_commit_behavior"
    assert result["current_belief"]["value"] == "confirm_first"
    assert result["belief_at_as_of"]["value"] == "confirm_first"
    assert [item["value"] for item in result["beliefs"][:2]] == [
        "confirm_first",
        "disabled",
    ]
    assert {item["key"] for item in result["genes"]} == {"git_commit_behavior"}
    assert result["capsules"][0]["scope"] == "project"
    assert {item["action"] for item in result["events"]} >= {"promote", "supersede"}
    assert {item["kind"] for item in result["timeline"]} >= {"belief", "event"}
