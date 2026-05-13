from __future__ import annotations

import re
from typing import Any, Mapping


LONG_TERM_MEMORY_TIERS = frozenset({"project_memory", "user_preference"})
MEMORY_CONTRACT_STATUS_NOT_APPLICABLE = "not_applicable"
MEMORY_CONTRACT_STATUS_TRUSTED = "trusted_long_term"
MEMORY_CONTRACT_STATUS_LEGACY = "legacy_compatible"
MEMORY_CONTRACT_STATUS_DOWNGRADED = "downgraded"
MEMORY_CONTRACT_STATUS_REJECTED = "rejected"
GLOBAL_MEMORY_WING = "global-memory"
DEFAULT_MEMORY_CONFIDENCE = 0.0
DEFAULT_MEMORY_SOURCE_COUNT = 0


PREFERENCE_PATTERNS = [
    re.compile(r"以后.*用"),
    re.compile(r"默认"),
    re.compile(r"请用"),
    re.compile(r"please use"),
    re.compile(r"by default"),
    re.compile(r"default to"),
    re.compile(r"prefer"),
    re.compile(r"always"),
]

PROJECT_PATTERNS = [
    re.compile(r"这个项目"),
    re.compile(r"当前项目"),
    re.compile(r"本项目"),
    re.compile(r"这个仓库"),
    re.compile(r"当前仓库"),
    re.compile(r"this project"),
    re.compile(r"this repo"),
    re.compile(r"this repository"),
    re.compile(r"in this repo"),
    re.compile(r"in this repository"),
    re.compile(r"未经确认"),
    re.compile(r"分析问题"),
]

CONSTRAINT_PATTERNS = [
    re.compile(r"不要"),
    re.compile(r"不能"),
    re.compile(r"禁止"),
    re.compile(r"必须"),
    re.compile(r"都要"),
    re.compile(r"do not"),
    re.compile(r"don't"),
    re.compile(r"before confirmation"),
    re.compile(r"only"),
    re.compile(r"must"),
]

TEST_PATTERNS = [
    re.compile(r"跑测试"),
    re.compile(r"运行测试"),
    re.compile(r"pytest"),
    re.compile(r"test"),
]

LOW_SIGNAL_WORKING_SESSION_TEXTS = {
    "继续",
    "开始",
    "开始实施",
    "提交",
    "同意",
    "收到",
    "重启了",
}

ASSISTANT_PROGRESS_PATTERNS = [
    re.compile(r"^(我先|我会先|我再|我准备|我现在|我继续|接下来我)"),
    re.compile(r"^(先检查|再检查|然后看|最后检查)"),
]

ASSISTANT_ANALYSIS_SIGNAL_PATTERNS = [
    re.compile(
        r"根因|原因|因为|导致|所以|说明|表明|结论|发现|已经|返回|缺少|不一致|冲突|失败|成功|需要|应该"
    ),
]


def classify_memory_tier(role: str | None, text: str) -> str:
    normalized_role = (role or "").strip().lower()
    normalized_text = (text or "").strip().lower()
    if normalized_role == "user" and any(
        pattern.search(normalized_text) for pattern in PREFERENCE_PATTERNS
    ):
        return "user_preference"
    if normalized_role == "user":
        if any(pattern.search(normalized_text) for pattern in PROJECT_PATTERNS) and any(
            pattern.search(normalized_text) for pattern in CONSTRAINT_PATTERNS
        ):
            return "project_memory"
        if any(pattern.search(normalized_text) for pattern in PROJECT_PATTERNS) and any(
            pattern.search(normalized_text) for pattern in TEST_PATTERNS
        ):
            return "project_memory"
    return "working_session"


def should_skip_memory_capture(role: str | None, text: str, memory_tier: str) -> bool:
    normalized_role = (role or "").strip().lower()
    normalized_text = " ".join((text or "").split()).strip().lower()

    if not normalized_text:
        return True
    if memory_tier != "working_session":
        return False
    if normalized_text in LOW_SIGNAL_WORKING_SESSION_TEXTS:
        return True
    if normalized_role != "assistant":
        return False
    if not any(
        pattern.match(normalized_text) for pattern in ASSISTANT_PROGRESS_PATTERNS
    ):
        return False
    return not any(
        pattern.search(normalized_text)
        for pattern in ASSISTANT_ANALYSIS_SIGNAL_PATTERNS
    )


def derive_memory_key(memory_tier: str, text: str) -> str | None:
    normalized_text = (text or "").strip().lower()
    if memory_tier == "user_preference":
        if any(
            token in normalized_text for token in ["中文", "英文", "english", "chinese"]
        ):
            return "response_language"
        if any(
            token in normalized_text
            for token in ["简洁", "详细", "concise", "brief", "verbose", "detailed"]
        ):
            return "response_detail"
    if memory_tier == "project_memory":
        if "git commit" in normalized_text or "提交" in normalized_text:
            return "git_commit_behavior"
        if any(pattern.search(normalized_text) for pattern in TEST_PATTERNS):
            return "test_execution_behavior"
        if any(
            token in normalized_text
            for token in ["修改代码", "改代码", "change code", "modify code"]
        ):
            if any(
                token in normalized_text
                for token in ["确认", "confirm", "confirmation"]
            ) and any(
                token in normalized_text
                for token in ["不要", "不能", "禁止", "do not", "don't", "before"]
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
        if "chinese" in normalized_text:
            return "zh-cn"
        if "英文" in normalized_text or "english" in normalized_text:
            return "en"
    if memory_key == "response_detail":
        if any(token in normalized_text for token in ["简洁", "concise", "brief"]):
            return "brief"
        if any(token in normalized_text for token in ["详细", "verbose", "detailed"]):
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
        if any(
            token in normalized_text for token in ["确认", "confirm", "confirmation"]
        ) and any(
            token in normalized_text
            for token in ["不要", "不能", "禁止", "do not", "don't", "before"]
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


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_directory(value: Any) -> str | None:
    text = _coerce_text(value)
    if text is None:
        return None
    normalized = text.replace("\\", "/").rstrip("/")
    return normalized or "/"


def _coerce_float(value: Any, default: float = DEFAULT_MEMORY_CONFIDENCE) -> float:
    try:
        return max(0.0, min(float(value), 1.0))
    except (TypeError, ValueError):
        return default


def _coerce_int(value: Any, default: int = DEFAULT_MEMORY_SOURCE_COUNT) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return True


def _coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw_items = value
    else:
        text = _coerce_text(value)
        if text is None:
            return []
        raw_items = re.split(r"[,;\n]+", text)
    normalized = []
    for item in raw_items:
        text = _coerce_text(item)
        if text:
            normalized.append(text)
    return normalized


def _candidate_metadata(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    metadata = candidate.get("metadata")
    if isinstance(metadata, Mapping):
        return metadata
    return {}


def _contract_value(
    candidate: Mapping[str, Any], metadata: Mapping[str, Any], *keys: str
) -> Any:
    for key in keys:
        value = candidate.get(key)
        if value not in (None, ""):
            return value
        value = metadata.get(key)
        if value not in (None, ""):
            return value
    return None


def normalize_memory_contract(candidate: Mapping[str, Any]) -> dict[str, Any]:
    metadata = _candidate_metadata(candidate)

    memory_tier = (
        _coerce_text(_contract_value(candidate, metadata, "memory_tier"))
        or "working_session"
    ).lower()
    directory = _coerce_directory(_contract_value(candidate, metadata, "directory"))
    wing = _coerce_text(_contract_value(candidate, metadata, "wing"))
    session_id = _coerce_text(_contract_value(candidate, metadata, "session_id"))
    message_id = _coerce_text(_contract_value(candidate, metadata, "message_id"))
    source_file = _coerce_text(_contract_value(candidate, metadata, "source_file"))
    filed_at = _coerce_text(_contract_value(candidate, metadata, "filed_at"))
    valid_from = _coerce_text(_contract_value(candidate, metadata, "valid_from"))
    valid_to = _coerce_text(_contract_value(candidate, metadata, "valid_to"))
    if valid_from is None and filed_at is not None:
        valid_from = filed_at
    if filed_at is None and valid_from is not None:
        filed_at = valid_from

    raw_confidence = _contract_value(candidate, metadata, "confidence")
    raw_source_count = _contract_value(candidate, metadata, "source_count")
    confidence = _coerce_float(raw_confidence)
    source_count = _coerce_int(
        raw_source_count,
        default=1 if (source_file or session_id or message_id) else 0,
    )

    superseded_by = _coerce_text(_contract_value(candidate, metadata, "superseded_by"))
    conflict_reason = _coerce_text(
        _contract_value(candidate, metadata, "conflict_reason", "conflict")
    )
    conflict_drawer_ids = _coerce_string_list(
        _contract_value(
            candidate,
            metadata,
            "conflict_drawer_ids",
            "conflict_drawer_id",
            "conflicts",
        )
    )
    demoted_at = _coerce_text(_contract_value(candidate, metadata, "demoted_at"))
    is_stale = _coerce_bool(
        _contract_value(candidate, metadata, "is_stale", "stale")
    ) or bool(valid_to)
    source = source_file or (f"session:{session_id}" if session_id else None)
    defaults_applied = []
    if raw_confidence is None:
        defaults_applied.append("confidence")
    if raw_source_count is None:
        defaults_applied.append("source_count")

    return {
        "memory_tier": memory_tier,
        "directory": directory,
        "wing": wing,
        "session_id": session_id,
        "message_id": message_id,
        "source_file": source_file,
        "source": source,
        "filed_at": filed_at,
        "confidence": confidence,
        "source_count": source_count,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "superseded_by": superseded_by,
        "conflict_reason": conflict_reason,
        "conflict_drawer_ids": conflict_drawer_ids,
        "demoted_at": demoted_at,
        "is_stale": is_stale,
        "namespace": {
            "directory": directory,
            "wing": wing,
            "session_id": session_id,
            "source_file": source_file,
            "source": source,
        },
        "provenance": {
            "session_id": session_id,
            "message_id": message_id,
            "filed_at": filed_at,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "confidence": confidence,
            "source_count": source_count,
        },
        "conflict": {
            "superseded_by": superseded_by,
            "conflict_reason": conflict_reason,
            "conflict_drawer_ids": conflict_drawer_ids,
            "demoted_at": demoted_at,
            "is_stale": is_stale,
        },
        "defaults_applied": defaults_applied,
    }


def assess_memory_contract(
    candidate: Mapping[str, Any],
    *,
    current_directory: str | None = None,
    current_wing: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_memory_contract(candidate)
    reasons: list[str] = []

    memory_tier = normalized["memory_tier"]
    if memory_tier not in LONG_TERM_MEMORY_TIERS:
        return {
            **normalized,
            "status": MEMORY_CONTRACT_STATUS_NOT_APPLICABLE,
            "eligible_for_context": True,
            "reasons": ["non_long_term"],
        }

    directory = normalized["directory"]
    wing = normalized["wing"]
    source_file = normalized["source_file"]
    session_id = normalized["session_id"]
    message_id = normalized["message_id"]

    identity_provenance = bool(source_file and session_id and message_id)
    partial_provenance = bool(
        source_file
        or session_id
        or message_id
        or normalized["filed_at"]
        or normalized["valid_from"]
    )
    namespace_complete = bool(wing) and (
        memory_tier != "project_memory" or bool(directory)
    )

    if current_wing and wing and wing not in {current_wing, GLOBAL_MEMORY_WING}:
        reasons.append("foreign_wing")
        status = MEMORY_CONTRACT_STATUS_REJECTED
    elif (
        memory_tier == "project_memory"
        and current_directory
        and directory
        and directory != current_directory
    ):
        reasons.append("foreign_directory")
        status = MEMORY_CONTRACT_STATUS_REJECTED
    elif memory_tier == "project_memory" and not directory:
        reasons.append("missing_directory")
        status = (
            MEMORY_CONTRACT_STATUS_DOWNGRADED
            if partial_provenance
            else MEMORY_CONTRACT_STATUS_REJECTED
        )
    elif not namespace_complete:
        if not wing:
            reasons.append("missing_wing")
        if memory_tier == "project_memory" and not directory:
            reasons.append("missing_directory")
        status = (
            MEMORY_CONTRACT_STATUS_DOWNGRADED
            if partial_provenance
            else MEMORY_CONTRACT_STATUS_REJECTED
        )
    elif identity_provenance and normalized["valid_from"]:
        status = MEMORY_CONTRACT_STATUS_TRUSTED
    elif partial_provenance:
        reasons.append("missing_provenance")
        status = MEMORY_CONTRACT_STATUS_LEGACY
    else:
        reasons.append("missing_provenance")
        status = MEMORY_CONTRACT_STATUS_DOWNGRADED

    if status == MEMORY_CONTRACT_STATUS_TRUSTED and (
        normalized["superseded_by"]
        or normalized["conflict_reason"]
        or normalized["conflict_drawer_ids"]
        or normalized["demoted_at"]
        or normalized["is_stale"]
        or normalized["valid_to"]
    ):
        reasons.append("conflict_or_stale_metadata")
        status = MEMORY_CONTRACT_STATUS_DOWNGRADED

    reasons = list(dict.fromkeys(reasons)) or ["trusted"]
    return {
        **normalized,
        "status": status,
        "eligible_for_context": status == MEMORY_CONTRACT_STATUS_TRUSTED,
        "reasons": reasons,
    }


__all__ = [
    "assess_memory_contract",
    "classify_memory_tier",
    "GLOBAL_MEMORY_WING",
    "LONG_TERM_MEMORY_TIERS",
    "MEMORY_CONTRACT_STATUS_DOWNGRADED",
    "MEMORY_CONTRACT_STATUS_LEGACY",
    "MEMORY_CONTRACT_STATUS_NOT_APPLICABLE",
    "MEMORY_CONTRACT_STATUS_REJECTED",
    "MEMORY_CONTRACT_STATUS_TRUSTED",
    "derive_memory_key",
    "derive_memory_value",
    "normalize_memory_contract",
    "should_skip_memory_capture",
]
