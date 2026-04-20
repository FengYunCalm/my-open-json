#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "references" / "catalog.md"
MATCHING_CUES = ROOT / "references" / "matching-cues.md"
UPSTREAM_DESIGN_DIR = ROOT / "references" / "upstream" / "design-md"

CATALOG_CATEGORY_RE = re.compile(r"^## (.+)$")
CATALOG_ENTRY_RE = re.compile(
    r"^- (?P<name>.+?) \| slug: (?P<slug>.+?) \| url: (?P<url>https://getdesign\.md/[^ ]+) \| (?P<summary>.+)$"
)
SECTION_RE = re.compile(r"^## (.+)$")
PRIMARY_RE = re.compile(r"^- Primary: (.+)$")
ALTERNATES_RE = re.compile(r"^- Alternates: (.+)$")
USE_RE = re.compile(r"^- Use when the request mentions: (.+)$")
LATIN_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9.+-]*")
SEPARATOR_RE = re.compile(r"[./_-]+")

STOPWORDS = {
    "a",
    "an",
    "and",
    "app",
    "build",
    "component",
    "design",
    "for",
    "feel",
    "in",
    "inspired",
    "interface",
    "like",
    "page",
    "product",
    "site",
    "style",
    "system",
    "that",
    "the",
    "to",
    "ui",
    "web",
}

CATEGORY_HINTS = {
    "AI & LLM Platforms": ["ai", "llm", "model", "agent", "assistant", "大模型", "模型", "智能体", "助手"],
    "Developer Tools & IDEs": ["developer", "devtool", "ide", "code", "coding", "terminal", "开发者", "代码", "编程", "终端"],
    "Backend, Database & DevOps": ["backend", "infra", "api", "database", "analytics", "监控", "后端", "数据库", "基础设施", "运维"],
    "Productivity & SaaS": ["saas", "docs", "productivity", "workspace", "文档", "效率", "工作流", "产品"],
    "Design & Creative Tools": ["design", "creative", "visual", "canvas", "设计", "创意", "视觉"],
    "Fintech & Crypto": ["fintech", "crypto", "bank", "payment", "交易", "金融", "支付", "加密"],
    "E-commerce & Retail": ["commerce", "retail", "store", "shopping", "零售", "电商", "商店"],
    "Media & Consumer Tech": ["consumer", "media", "editorial", "content", "消费", "媒体", "内容"],
    "Automotive": ["auto", "car", "vehicle", "汽车", "跑车", "座舱"],
}


@dataclass
class Entry:
    name: str
    slug: str
    url: str
    summary: str
    category: str
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)

    @property
    def stub_path(self) -> Path:
        return UPSTREAM_DESIGN_DIR / self.slug / "README.md"

    @property
    def variants(self) -> set[str]:
        variants = {self.name.lower(), self.slug.lower()}
        variants.add(self.name.lower().replace(".", ""))
        variants.add(self.slug.lower().replace(".", ""))
        return {item for item in variants if len(item) >= 3}

    @property
    def exact_variants(self) -> list[str]:
        variants: set[str] = set()
        for raw in (self.name, self.slug):
            lowered = raw.lower().strip()
            if not lowered:
                continue
            variants.add(lowered)

            separated = normalize_text(SEPARATOR_RE.sub(" ", lowered))
            variants.add(separated)
            variants.add(separated.replace(" ", ""))

        return sorted((variant for variant in variants if len(variant) >= 3), key=len, reverse=True)

    @property
    def tokens(self) -> set[str]:
        source = f"{self.name} {self.slug} {self.category} {self.summary}".lower()
        return {token for token in LATIN_TOKEN_RE.findall(source) if token not in STOPWORDS}


@dataclass
class CueSection:
    title: str
    primary: str
    alternates: list[str]
    phrases: list[str]


def load_entries() -> list[Entry]:
    entries: list[Entry] = []
    category = "Uncategorized"

    for raw_line in CATALOG.read_text().splitlines():
        line = raw_line.strip()
        category_match = CATALOG_CATEGORY_RE.match(line)
        if category_match:
            category = category_match.group(1)
            continue

        entry_match = CATALOG_ENTRY_RE.match(line)
        if entry_match:
            entries.append(Entry(category=category, **entry_match.groupdict()))

    return entries


def load_cues() -> list[CueSection]:
    sections: list[CueSection] = []
    current: dict[str, object] = {}

    for raw_line in MATCHING_CUES.read_text().splitlines():
        line = raw_line.strip()
        section_match = SECTION_RE.match(line)
        if section_match:
            if current:
                sections.append(
                    CueSection(
                        title=current["title"],
                        primary=current["primary"],
                        alternates=current["alternates"],
                        phrases=current["phrases"],
                    )
                )
            current = {
                "title": section_match.group(1),
                "primary": "",
                "alternates": [],
                "phrases": [],
            }
            continue

        primary_match = PRIMARY_RE.match(line)
        if primary_match and current:
            current["primary"] = primary_match.group(1).strip()
            continue

        alternates_match = ALTERNATES_RE.match(line)
        if alternates_match and current:
            current["alternates"] = [part.strip() for part in alternates_match.group(1).split(",") if part.strip()]
            continue

        use_match = USE_RE.match(line)
        if use_match and current:
            current["phrases"] = [part.strip().lower() for part in use_match.group(1).split(",") if part.strip()]

    if current:
        sections.append(
            CueSection(
                title=current["title"],
                primary=current["primary"],
                alternates=current["alternates"],
                phrases=current["phrases"],
            )
        )

    return sections


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def tokenize_latin(text: str) -> set[str]:
    return {token for token in LATIN_TOKEN_RE.findall(text.lower()) if token not in STOPWORDS}


def add_reason(entry: Entry, reason: str) -> None:
    if reason not in entry.reasons:
        entry.reasons.append(reason)


def has_exact_variant(prompt_norm: str, variant: str) -> bool:
    pattern = rf"(?<![a-z0-9]){re.escape(variant)}(?![a-z0-9])"
    return re.search(pattern, prompt_norm) is not None


def apply_exact_match_scores(prompt_norm: str, entries: list[Entry]) -> None:
    for entry in entries:
        for variant in entry.exact_variants:
            if has_exact_variant(prompt_norm, variant):
                entry.score += 140
                add_reason(entry, f"exact brand match: {variant}")
                break


def apply_cue_scores(prompt_norm: str, entries: list[Entry], sections: list[CueSection]) -> None:
    by_name = {entry.name.lower(): entry for entry in entries}

    for section in sections:
        matched = [phrase for phrase in section.phrases if phrase and phrase in prompt_norm]
        if not matched:
            continue

        primary = by_name.get(section.primary.lower())
        if primary:
            primary.score += 60 + 8 * len(matched)
            add_reason(primary, f"cue match: {section.title} via {', '.join(matched[:4])}")

        for alt_name in section.alternates:
            alt = by_name.get(alt_name.lower())
            if alt:
                alt.score += 30 + 4 * len(matched)
                add_reason(alt, f"alternate cue: {section.title}")


def apply_token_scores(prompt_tokens: set[str], entries: list[Entry]) -> None:
    for entry in entries:
        overlap = sorted(prompt_tokens & entry.tokens)
        if overlap:
            entry.score += 5 * len(overlap)
            add_reason(entry, f"token overlap: {', '.join(overlap[:5])}")


def apply_category_scores(prompt_norm: str, entries: list[Entry]) -> None:
    for entry in entries:
        hints = CATEGORY_HINTS.get(entry.category, [])
        matched = [hint for hint in hints if hint in prompt_norm]
        if matched:
            entry.score += 12 + len(matched)
            add_reason(entry, f"category fit: {entry.category}")


def rank_entries(prompt: str) -> list[Entry]:
    entries = load_entries()
    cue_sections = load_cues()
    prompt_norm = normalize_text(prompt)
    prompt_tokens = tokenize_latin(prompt)

    apply_exact_match_scores(prompt_norm, entries)
    apply_cue_scores(prompt_norm, entries, cue_sections)
    apply_token_scores(prompt_tokens, entries)
    apply_category_scores(prompt_norm, entries)

    ranked = [entry for entry in entries if entry.score > 0]
    ranked.sort(key=lambda item: (-item.score, item.name.lower()))
    return ranked


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank awesome-design references for a user prompt")
    parser.add_argument("prompt", nargs="?", help="User request to match against the local catalog")
    parser.add_argument("--top", type=int, default=3, help="Number of ranked results to print")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text")
    return parser.parse_args()


def read_prompt(args: argparse.Namespace) -> str:
    if args.prompt:
        return args.prompt.strip()

    piped = sys.stdin.read().strip()
    if piped:
        return piped

    raise SystemExit("Provide a prompt as an argument or via stdin")


def render_text(prompt: str, ranked: list[Entry], top: int) -> str:
    lines = [f"Prompt: {prompt}", ""]
    if not ranked:
        lines.append("No confident local match.")
        return "\n".join(lines)

    lines.append("Top matches:")
    for index, entry in enumerate(ranked[:top], start=1):
        lines.append(f"{index}. {entry.name} ({entry.slug}) score={entry.score:.0f}")
        lines.append(f"   Category: {entry.category}")
        lines.append(f"   URL: {entry.url}")
        lines.append(f"   Local stub: {entry.stub_path}")
        lines.append(f"   Summary: {entry.summary}")
        for reason in entry.reasons[:4]:
            lines.append(f"   Reason: {reason}")
        lines.append("")

    return "\n".join(lines).rstrip()


def render_json(ranked: list[Entry], top: int) -> str:
    payload = []
    for entry in ranked[:top]:
        payload.append(
            {
                "name": entry.name,
                "slug": entry.slug,
                "category": entry.category,
                "url": entry.url,
                "summary": entry.summary,
                "score": round(entry.score, 2),
                "reasons": entry.reasons,
                "local_stub": str(entry.stub_path),
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def main() -> None:
    args = parse_args()
    prompt = read_prompt(args)
    ranked = rank_entries(prompt)
    if args.json:
        print(render_json(ranked, args.top))
    else:
        print(render_text(prompt, ranked, args.top))


if __name__ == "__main__":
    main()
