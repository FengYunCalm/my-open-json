from __future__ import annotations

import sys
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_evomemory_package import PromotionBackend


def test_export_archive_includes_context_runtime_and_all_planes():
    from evomemory.context.bridge import BridgeConfig, BridgeCore

    temp_dir = Path(tempfile.mkdtemp(prefix="evomemory-archive-export-"))
    state_path = temp_dir / "state.sqlite3"
    core = BridgeCore(BridgeConfig(state_path=state_path), backend=PromotionBackend())
    core.start_session("ses_archive_export", "/home/mechrevo/.config/opencode")
    core.flush_session(
        "ses_archive_export",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_archive_export_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_archive_export_2", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    core.flush_session(
        "ses_archive_export",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_archive_export_3", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
            {
                "info": {"id": "msg_archive_export_4", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里还是不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    core.search_context(
        "git commit",
        "/home/mechrevo/.config/opencode",
        session_id="ses_archive_export",
    )

    archive = core.evomemory_export_archive(limit=10)

    assert archive["format"] == "evomemory-archive-v1"
    assert archive["context"]["drawer_count"] >= 2
    assert archive["belief"]["count"] >= 2
    assert archive["governance"]["gene_count"] >= 2
    assert archive["governance"]["capsule_count"] >= 1
    assert archive["runtime"]["last_search_summary"] is not None
    assert archive["summary"]["drawer_count"] == archive["context"]["drawer_count"]


def test_import_archive_dry_run_reports_counts_without_mutation():
    from evomemory.context.bridge import BridgeConfig, BridgeCore

    source_dir = Path(tempfile.mkdtemp(prefix="evomemory-archive-dryrun-source-"))
    source = BridgeCore(
        BridgeConfig(state_path=source_dir / "state.sqlite3"), backend=PromotionBackend()
    )
    source.start_session("ses_archive_dryrun", "/home/mechrevo/.config/opencode")
    source.flush_session(
        "ses_archive_dryrun",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_archive_dryrun_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            }
        ],
        reason="idle",
    )
    source.flush_session(
        "ses_archive_dryrun",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_archive_dryrun_2", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            }
        ],
        reason="idle",
    )
    archive = source.evomemory_export_archive(limit=10)

    target_dir = Path(tempfile.mkdtemp(prefix="evomemory-archive-dryrun-target-"))
    target = BridgeCore(
        BridgeConfig(state_path=target_dir / "state.sqlite3"), backend=PromotionBackend()
    )

    result = target.evomemory_import_archive(archive=archive, dry_run=True)

    assert result["dry_run"] is True
    assert result["summary"]["beliefs"]["new"] >= 1
    assert target.evomemory_query_beliefs(limit=10)["count"] == 0
    assert target.repository.list_drawers(limit=10, offset=0) == []


def test_import_archive_restores_archive_into_fresh_core():
    from evomemory.context.bridge import BridgeConfig, BridgeCore

    source_dir = Path(tempfile.mkdtemp(prefix="evomemory-archive-import-source-"))
    source = BridgeCore(
        BridgeConfig(state_path=source_dir / "state.sqlite3"), backend=PromotionBackend()
    )
    source.start_session("ses_archive_import", "/home/mechrevo/.config/opencode")
    source.flush_session(
        "ses_archive_import",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_archive_import_1", "role": "user"},
                "parts": [{"type": "text", "text": "以后都用中文回复"}],
            },
            {
                "info": {"id": "msg_archive_import_2", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    source.flush_session(
        "ses_archive_import",
        "/home/mechrevo/.config/opencode",
        [
            {
                "info": {"id": "msg_archive_import_3", "role": "user"},
                "parts": [{"type": "text", "text": "默认也用中文回复"}],
            },
            {
                "info": {"id": "msg_archive_import_4", "role": "user"},
                "parts": [
                    {"type": "text", "text": "这个项目里还是不要自动提交 git commit"}
                ],
            },
        ],
        reason="idle",
    )
    archive = source.evomemory_export_archive(limit=10)

    target_dir = Path(tempfile.mkdtemp(prefix="evomemory-archive-import-target-"))
    target = BridgeCore(
        BridgeConfig(state_path=target_dir / "state.sqlite3"), backend=PromotionBackend()
    )

    result = target.evomemory_import_archive(archive=archive, dry_run=False)

    assert result["dry_run"] is False
    assert result["imported"]["beliefs"]["created_count"] >= 2
    assert target.evomemory_query_beliefs(limit=10)["count"] >= 2
    assert target.evomemory_query_genes(limit=10)["count"] >= 2
    assert len(target.repository.list_drawers(limit=10, offset=0)) >= 2
