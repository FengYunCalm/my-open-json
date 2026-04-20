#!/usr/bin/env python3
"""Quick validation script for skills - minimal version."""

import re
import sys
from pathlib import Path


ALLOWED_PROPERTIES = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}
BLOCK_SCALAR_KEYS = {"description", "compatibility"}
MAPPING_KEYS = {"metadata"}
LIST_KEYS = {"allowed-tools"}

_ENTRY_RE = re.compile(r"^([A-Za-z0-9-]+):(.*)$")
_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(?:\d+\.\d*|\.\d+|\d+\.\d+)(?:[eE][+-]?\d+)?$")


def _parse_scalar(raw_value: str):
    value = raw_value.strip()

    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]

    lower = value.lower()
    if lower in {"null", "~"}:
        return None
    if lower == "true":
        return True
    if lower == "false":
        return False
    if _INT_RE.match(value):
        return int(value)
    if _FLOAT_RE.match(value):
        return float(value)

    return value


def _collect_indented_lines(lines: list[str], start_index: int):
    block_lines: list[str] = []
    i = start_index

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            block_lines.append("")
            i += 1
            continue

        if line.startswith("\t"):
            return None, i, "Tabs are not supported in frontmatter indentation"

        if line.startswith(" "):
            block_lines.append(line)
            i += 1
            continue

        break

    return block_lines, i, None


def _parse_block_scalar(block_lines: list[str], style: str) -> str:
    if style == "|":
        return "\n".join(line.lstrip(" ") for line in block_lines).rstrip()

    paragraphs: list[str] = []
    current: list[str] = []

    for line in block_lines:
        if line == "":
            if current:
                paragraphs.append(" ".join(current))
                current = []
            else:
                paragraphs.append("")
        else:
            current.append(line.lstrip(" "))

    if current:
        paragraphs.append(" ".join(current))

    return "\n".join(paragraphs).rstrip()


def _parse_metadata_block(block_lines: list[str]):
    metadata = {}

    for line in block_lines:
        if not line:
            continue

        if not line.startswith("  "):
            return (
                None,
                f"Metadata entries must be indented by at least two spaces: {line}",
            )

        entry = line.lstrip(" ")
        match = _ENTRY_RE.match(entry)
        if not match:
            return None, f"Invalid metadata entry: {line}"

        key = match.group(1)
        raw_value = match.group(2).strip()

        if key in metadata:
            return None, f"Duplicate metadata key: {key}"

        if not raw_value:
            return None, f"Metadata value for '{key}' must be a scalar"

        if raw_value.startswith("{") or raw_value.startswith("["):
            return None, f"Metadata value for '{key}' must be a scalar"

        value = _parse_scalar(raw_value)
        if not isinstance(value, str):
            return (
                None,
                f"Metadata value for '{key}' must be a string, got {type(value).__name__}",
            )

        metadata[key] = value

    return metadata, None


def _parse_allowed_tools_block(block_lines: list[str]):
    tools = []

    for line in block_lines:
        if not line:
            continue

        if not line.startswith("  - "):
            return None, f"Invalid allowed-tools entry: {line}"

        stripped = line.lstrip(" ")
        if not stripped.startswith("- "):
            return None, f"Invalid allowed-tools entry: {line}"

        raw_item = stripped[2:].strip()
        if not raw_item:
            return None, "allowed-tools entries cannot be empty"
        if raw_item.startswith("{") or raw_item.startswith("["):
            return None, "allowed-tools entries must be strings"

        item = _parse_scalar(raw_item)
        if not isinstance(item, str):
            return (
                None,
                f"allowed-tools entries must be strings, got {type(item).__name__}",
            )

        tools.append(item)

    return tools, None


def _parse_allowed_tools_inline(raw_value: str):
    if not (raw_value.startswith("[") and raw_value.endswith("]")):
        return None, "allowed-tools must be a list"

    inner = raw_value[1:-1].strip()
    if not inner:
        return [], None

    tools = []
    for part in inner.split(","):
        item = part.strip()
        if not item:
            return None, "allowed-tools entries cannot be empty"
        if item.startswith("{") or item.startswith("["):
            return None, "allowed-tools entries must be strings"

        parsed = _parse_scalar(item)
        if not isinstance(parsed, str):
            return (
                None,
                f"allowed-tools entries must be strings, got {type(parsed).__name__}",
            )
        tools.append(parsed)

    return tools, None


def _parse_frontmatter(frontmatter_text: str):
    frontmatter = {}
    lines = frontmatter_text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        if line.startswith((" ", "\t")):
            return None, f"Unexpected indentation at top level: {line}"

        match = _ENTRY_RE.match(line)
        if not match:
            return None, f"Invalid frontmatter line: {line}"

        key = match.group(1)
        raw_value = match.group(2).strip()

        if key in frontmatter:
            return None, f"Duplicate frontmatter key: {key}"

        if raw_value in {"|", "|-", ">", ">-"}:
            if key not in BLOCK_SCALAR_KEYS:
                return None, f"Unexpected block scalar under '{key}'"

            block_lines, next_index, error = _collect_indented_lines(lines, i + 1)
            if error:
                return None, error

            frontmatter[key] = _parse_block_scalar(block_lines, raw_value[0])
            i = next_index
            continue

        if key in MAPPING_KEYS:
            if raw_value:
                return None, f"'{key}' must use an indented mapping"

            block_lines, next_index, error = _collect_indented_lines(lines, i + 1)
            if error:
                return None, error

            if block_lines:
                value, error = _parse_metadata_block(block_lines)
                if error:
                    return None, error
                frontmatter[key] = value
            else:
                frontmatter[key] = {}

            i = next_index
            continue

        if key in LIST_KEYS:
            if raw_value:
                value, error = _parse_allowed_tools_inline(raw_value)
                if error:
                    return None, error
                frontmatter[key] = value
                i += 1
                continue

            block_lines, next_index, error = _collect_indented_lines(lines, i + 1)
            if error:
                return None, error

            if block_lines:
                value, error = _parse_allowed_tools_block(block_lines)
                if error:
                    return None, error
                frontmatter[key] = value
            else:
                frontmatter[key] = []

            i = next_index
            continue

        value = _parse_scalar(raw_value)
        frontmatter[key] = value

        next_index = i + 1
        while next_index < len(lines) and not lines[next_index].strip():
            next_index += 1
        if next_index < len(lines) and lines[next_index].startswith((" ", "\t")):
            return None, f"Unexpected nested block under '{key}'"

        i += 1

    return frontmatter, None


def validate_skill(skill_path):
    """Basic validation of a skill"""
    skill_path = Path(skill_path)

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found"

    content = skill_md.read_text()
    if not content.startswith("---"):
        return False, "No YAML frontmatter found"

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    frontmatter_text = match.group(1)

    frontmatter, error = _parse_frontmatter(frontmatter_text)
    if error:
        return False, error

    if not isinstance(frontmatter, dict):
        return False, "Frontmatter must be a dictionary"

    unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
    if unexpected_keys:
        return False, (
            f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}. "
            f"Allowed properties are: {', '.join(sorted(ALLOWED_PROPERTIES))}"
        )

    if "name" not in frontmatter:
        return False, "Missing 'name' in frontmatter"
    if "description" not in frontmatter:
        return False, "Missing 'description' in frontmatter"

    name = frontmatter.get("name", "")
    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name).__name__}"
    name = name.strip()
    if name:
        if not re.match(r"^[a-z0-9-]+$", name):
            return (
                False,
                f"Name '{name}' should be kebab-case (lowercase letters, digits, and hyphens only)",
            )
        if name.startswith("-") or name.endswith("-") or "--" in name:
            return (
                False,
                f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens",
            )
        if len(name) > 64:
            return (
                False,
                f"Name is too long ({len(name)} characters). Maximum is 64 characters.",
            )

    description = frontmatter.get("description", "")
    if not isinstance(description, str):
        return False, f"Description must be a string, got {type(description).__name__}"
    description = description.strip()
    if description:
        if "<" in description or ">" in description:
            return False, "Description cannot contain angle brackets (< or >)"
        if len(description) > 1024:
            return (
                False,
                f"Description is too long ({len(description)} characters). Maximum is 1024 characters.",
            )

    compatibility = frontmatter.get("compatibility", "")
    if compatibility:
        if not isinstance(compatibility, str):
            return (
                False,
                f"Compatibility must be a string, got {type(compatibility).__name__}",
            )
        if len(compatibility) > 500:
            return (
                False,
                f"Compatibility is too long ({len(compatibility)} characters). Maximum is 500 characters.",
            )

    metadata = frontmatter.get("metadata", {})
    if metadata and not isinstance(metadata, dict):
        return False, f"Metadata must be a mapping, got {type(metadata).__name__}"

    allowed_tools = frontmatter.get("allowed-tools", [])
    if allowed_tools and not isinstance(allowed_tools, list):
        return (
            False,
            f"allowed-tools must be a list, got {type(allowed_tools).__name__}",
        )
    if isinstance(allowed_tools, list) and any(
        not isinstance(item, str) for item in allowed_tools
    ):
        bad_type = next(
            type(item).__name__ for item in allowed_tools if not isinstance(item, str)
        )
        return False, f"allowed-tools entries must be strings, got {bad_type}"

    return True, "Skill is valid!"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quick_validate.py <skill_directory>")
        sys.exit(1)

    valid, message = validate_skill(sys.argv[1])
    print(message)
    sys.exit(0 if valid else 1)
