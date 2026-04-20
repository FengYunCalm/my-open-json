#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_README = ROOT / "references" / "upstream" / "README.md"
CATALOG = ROOT / "references" / "catalog.md"
UPSTREAM_DESIGN_DIR = ROOT / "references" / "upstream" / "design-md"

CATEGORY_RE = re.compile(r"^###\s+(.+)$")
ENTRY_RE = re.compile(
    r"^- \[\*\*(.+?)\*\*\]\((https://getdesign\.md/([^/]+)/design-md)\) - (.+)$"
)


@dataclass
class Entry:
    name: str
    slug: str
    url: str
    summary: str
    category: str


def parse_entries() -> list[Entry]:
    text = UPSTREAM_README.read_text()
    entries: list[Entry] = []
    category = "Uncategorized"

    for raw_line in text.splitlines():
        line = raw_line.strip()
        category_match = CATEGORY_RE.match(line)
        if category_match:
            category = category_match.group(1)
            continue

        entry_match = ENTRY_RE.match(line)
        if entry_match:
            name, url, slug, summary = entry_match.groups()
            entries.append(Entry(name=name, slug=slug, url=url, summary=summary, category=category))

    return entries


def build_catalog(entries: list[Entry]) -> str:
    lines = [
        "# Awesome Design Catalog",
        "",
        "Local catalog extracted from the `awesome-design-md` collection.",
        "Use this file for first-pass matching before trying external URLs.",
        "",
        "Entry format:",
        "`Name | slug: ... | url: ... | summary`",
    ]

    category = None
    for entry in entries:
        if entry.category != category:
            category = entry.category
            lines.extend(["", f"## {category}"])
        lines.append(
            f"- {entry.name} | slug: {entry.slug} | url: {entry.url} | {entry.summary}"
        )

    return "\n".join(lines).rstrip() + "\n"


def ensure_local_stubs(entries: list[Entry]) -> int:
    created = 0

    for entry in entries:
        stub_path = UPSTREAM_DESIGN_DIR / entry.slug / "README.md"
        if stub_path.exists():
            continue

        stub_path.parent.mkdir(parents=True, exist_ok=True)
        stub_path.write_text(
            "\n".join(
                [
                    f"# {entry.name} Inspired Design System",
                    "",
                    f"Design system details have been moved to: {entry.url}",
                    "",
                ]
            )
        )
        created += 1

    return created


def main() -> None:
    if not UPSTREAM_README.exists():
        raise SystemExit(f"Missing upstream README: {UPSTREAM_README}")

    entries = parse_entries()
    CATALOG.write_text(build_catalog(entries))
    created = ensure_local_stubs(entries)
    print(f"Wrote {CATALOG}")
    print(f"Backfilled {created} missing local stubs")


if __name__ == "__main__":
    main()
