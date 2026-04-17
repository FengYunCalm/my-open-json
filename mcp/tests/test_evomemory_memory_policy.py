from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evomemory.domain.memory_policy import (
    classify_memory_tier,
    derive_memory_key,
    derive_memory_value,
    should_skip_memory_capture,
)


def test_classify_memory_tier_detects_user_preference_constraints():
    assert (
        classify_memory_tier("user", "以后都用中文回复，默认简洁一点")
        == "user_preference"
    )


def test_classify_memory_tier_defaults_to_working_session():
    assert (
        classify_memory_tier("assistant", "我会先检查 bridge 和 state store")
        == "working_session"
    )


def test_classify_memory_tier_detects_project_constraints():
    assert (
        classify_memory_tier("user", "这个项目里不要自动提交 git commit")
        == "project_memory"
    )


def test_classify_memory_tier_does_not_promote_assistant_project_summaries():
    assert (
        classify_memory_tier(
            "assistant",
            "这个项目里不要自动提交 git commit，未经确认不要修改代码，修改后都要跑测试",
        )
        == "working_session"
    )


def test_should_skip_memory_capture_ignores_long_assistant_progress_updates():
    assert (
        should_skip_memory_capture(
            "assistant",
            "我会先检查 bridge 和 state store 的差异，再对一下当前会话的连接链路。",
            "working_session",
        )
        is True
    )


def test_should_skip_memory_capture_keeps_substantive_assistant_analysis():
    assert (
        should_skip_memory_capture(
            "assistant",
            "我检查了 bridge 和 state store，根因是 stdio 与 HTTP 双链路同时写同一套状态文件，导致当前会话和后台 bridge 的视图不一致。",
            "working_session",
        )
        is False
    )


def test_derive_memory_key_detects_response_language():
    assert (
        derive_memory_key("user_preference", "以后都用中文回复") == "response_language"
    )


def test_derive_memory_key_detects_response_detail():
    assert derive_memory_key("user_preference", "默认详细一点") == "response_detail"


def test_derive_memory_key_detects_git_commit_behavior():
    assert (
        derive_memory_key("project_memory", "这个项目里不要自动提交 git commit")
        == "git_commit_behavior"
    )


def test_derive_memory_key_detects_test_execution_behavior():
    assert (
        derive_memory_key("project_memory", "这个项目里每次修改后都要跑测试")
        == "test_execution_behavior"
    )


def test_derive_memory_key_detects_code_change_permission():
    assert (
        derive_memory_key("project_memory", "未经确认，不要修改代码")
        == "code_change_permission"
    )


def test_derive_memory_key_detects_implementation_mode_preference():
    assert (
        derive_memory_key("project_memory", "如果只是分析问题，先不要改代码")
        == "implementation_mode_preference"
    )


def test_derive_memory_value_normalizes_response_language():
    assert derive_memory_value("response_language", "以后都用中文回复") == "zh-cn"
    assert derive_memory_value("response_language", "以后都用英文回复") == "en"


def test_derive_memory_value_normalizes_git_commit_behavior():
    assert (
        derive_memory_value("git_commit_behavior", "这个项目里不要自动提交 git commit")
        == "disabled"
    )
    assert (
        derive_memory_value("git_commit_behavior", "这个项目里必须自动提交 git commit")
        == "required"
    )


def test_derive_memory_value_normalizes_response_detail():
    assert derive_memory_value("response_detail", "默认简洁一点") == "brief"
    assert derive_memory_value("response_detail", "默认详细一点") == "detailed"


def test_derive_memory_value_normalizes_test_execution_behavior():
    assert (
        derive_memory_value("test_execution_behavior", "这个项目里每次修改后都要跑测试")
        == "required"
    )
    assert (
        derive_memory_value("test_execution_behavior", "这个项目里先不要跑测试")
        == "disabled"
    )


def test_derive_memory_value_normalizes_code_change_permission():
    assert (
        derive_memory_value("code_change_permission", "未经确认，不要修改代码")
        == "confirm_first"
    )
    assert (
        derive_memory_value("code_change_permission", "现在可以直接改代码") == "allowed"
    )


def test_derive_memory_value_normalizes_implementation_mode_preference():
    assert (
        derive_memory_value(
            "implementation_mode_preference", "如果只是分析问题，先不要改代码"
        )
        == "read_only_first"
    )
    assert (
        derive_memory_value(
            "implementation_mode_preference", "默认直接实现，不用先给方案"
        )
        == "implement_directly"
    )
