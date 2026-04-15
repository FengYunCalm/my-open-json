from __future__ import annotations

import re


PREFERENCE_PATTERNS = [
    re.compile(r"以后.*用"),
    re.compile(r"默认"),
    re.compile(r"请用"),
    re.compile(r"prefer"),
    re.compile(r"always"),
]

PROJECT_PATTERNS = [
    re.compile(r"这个项目"),
    re.compile(r"当前项目"),
    re.compile(r"本项目"),
    re.compile(r"这个仓库"),
    re.compile(r"当前仓库"),
    re.compile(r"未经确认"),
    re.compile(r"分析问题"),
]

CONSTRAINT_PATTERNS = [
    re.compile(r"不要"),
    re.compile(r"不能"),
    re.compile(r"禁止"),
    re.compile(r"必须"),
    re.compile(r"都要"),
    re.compile(r"only"),
    re.compile(r"must"),
]

TEST_PATTERNS = [
    re.compile(r"跑测试"),
    re.compile(r"运行测试"),
    re.compile(r"pytest"),
    re.compile(r"test"),
]


def classify_memory_tier(role: str | None, text: str) -> str:
    normalized_role = (role or "").strip().lower()
    normalized_text = (text or "").strip().lower()
    if normalized_role == "user" and any(
        pattern.search(normalized_text) for pattern in PREFERENCE_PATTERNS
    ):
        return "user_preference"
    if any(pattern.search(normalized_text) for pattern in PROJECT_PATTERNS) and any(
        pattern.search(normalized_text) for pattern in CONSTRAINT_PATTERNS
    ):
        return "project_memory"
    if any(pattern.search(normalized_text) for pattern in PROJECT_PATTERNS) and any(
        pattern.search(normalized_text) for pattern in TEST_PATTERNS
    ):
        return "project_memory"
    return "working_session"


def derive_memory_key(memory_tier: str, text: str) -> str | None:
    normalized_text = (text or "").strip().lower()
    if memory_tier == "user_preference":
        if "中文" in normalized_text or "英文" in normalized_text:
            return "response_language"
        if "简洁" in normalized_text or "详细" in normalized_text:
            return "response_detail"
    if memory_tier == "project_memory":
        if "git commit" in normalized_text or "提交" in normalized_text:
            return "git_commit_behavior"
        if any(pattern.search(normalized_text) for pattern in TEST_PATTERNS):
            return "test_execution_behavior"
        if "修改代码" in normalized_text or "改代码" in normalized_text:
            if "确认" in normalized_text and any(
                token in normalized_text for token in ["不要", "不能", "禁止"]
            ):
                return "code_change_permission"
            if any(
                token in normalized_text for token in ["直接改代码", "可以直接改代码"]
            ):
                return "code_change_permission"
            if "分析问题" in normalized_text:
                return "implementation_mode_preference"
    return None


def derive_memory_value(memory_key: str | None, text: str) -> str | None:
    if not memory_key:
        return None
    normalized_text = (text or "").strip().lower()
    if memory_key == "response_language":
        if "中文" in normalized_text:
            return "zh-cn"
        if "英文" in normalized_text or "english" in normalized_text:
            return "en"
    if memory_key == "response_detail":
        if "简洁" in normalized_text:
            return "brief"
        if "详细" in normalized_text:
            return "detailed"
    if memory_key == "git_commit_behavior":
        if any(token in normalized_text for token in ["不要", "不能", "禁止"]):
            return "disabled"
        if any(token in normalized_text for token in ["必须", "必须要"]):
            return "required"
    if memory_key == "test_execution_behavior":
        if any(token in normalized_text for token in ["不要", "先不要", "暂时不要"]):
            return "disabled"
        if any(token in normalized_text for token in ["必须", "都要", "每次", "记得"]):
            return "required"
    if memory_key == "code_change_permission":
        if "确认" in normalized_text and any(
            token in normalized_text for token in ["不要", "不能", "禁止"]
        ):
            return "confirm_first"
        if any(token in normalized_text for token in ["直接改代码", "可以直接改代码"]):
            return "allowed"
    if memory_key == "implementation_mode_preference":
        if "分析问题" in normalized_text and any(
            token in normalized_text for token in ["不要", "先不要"]
        ):
            return "read_only_first"
        if any(
            token in normalized_text
            for token in ["直接实现", "默认直接实现", "不用先给方案"]
        ):
            return "implement_directly"
    return normalized_text or None
