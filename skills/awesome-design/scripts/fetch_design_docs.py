#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "references" / "catalog.md"
DESIGN_ROOT = ROOT / "references" / "upstream" / "design-md"
POWERSHELL = shutil.which("powershell.exe")
EDGE = Path("/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")

ENTRY_RE = re.compile(
    r"^- (?P<name>.+?) \| slug: (?P<slug>.+?) \| url: https://getdesign\.md/(?P<url_slug>.+?)/design-md \| (?P<summary>.+)$"
)
PRE_RE = re.compile(r"<pre[^>]*>(?P<content>[\s\S]*?)</pre>", re.IGNORECASE)


def parse_catalog() -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line in CATALOG.read_text().splitlines():
        match = ENTRY_RE.match(line.strip())
        if match:
            entries.append((match.group("slug"), match.group("name")))
    return entries


def repair_mojibake(text: str) -> str:
    candidates = [text]

    try:
        candidates.append(text.encode("latin1").decode("utf-8"))
    except Exception:  # noqa: BLE001
        pass

    def score(value: str) -> tuple[int, int]:
        bad_markers = ["â", "鈥", "�", "Ã", "¤", "¢"]
        bad = sum(value.count(marker) for marker in bad_markers)
        return (bad, -sum(ord(ch) > 127 for ch in value))

    return min(candidates, key=score)


def fetch_markdown_via_powershell(slug: str) -> str:
    url = f"https://getdesign.md/design-md/{slug}/DESIGN.md"
    command = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        f"(Invoke-WebRequest -UseBasicParsing -Uri '{url}').Content"
    )
    result = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-Command",
            command,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    if result.returncode != 0 and not result.stdout:
        raise RuntimeError(f"PowerShell fetch failed for {slug}: {result.stderr.strip()}")

    return repair_mojibake(result.stdout)


def fetch_markdown_via_edge(slug: str) -> str:
    if not EDGE.exists():
        raise RuntimeError(f"Missing Edge executable: {EDGE}")

    url = f"https://getdesign.md/design-md/{slug}/DESIGN.md"
    result = subprocess.run(
        [
            str(EDGE),
            "--headless=new",
            "--disable-gpu",
            "--dump-dom",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    if result.returncode != 0 and not result.stdout:
        raise RuntimeError(f"Edge fetch failed for {slug}: {result.stderr.strip()}")

    match = PRE_RE.search(result.stdout)
    if not match:
        snippet = result.stdout[:200].replace("\n", "\\n")
        raise RuntimeError(f"Edge fetch failed for {slug}: no <pre> markdown block found in {snippet}")

    return repair_mojibake(html.unescape(match.group("content")))


def normalize_content(content: str, slug: str) -> str:
    content = content.replace("\r\n", "\n")
    content = content.replace("\r", "\n")
    content = content.strip() + "\n"

    if "Design System Inspired by" not in content:
        snippet = content[:200].replace("\n", "\\n")
        raise RuntimeError(f"Unexpected content for {slug}: {snippet}")

    return content


def fetch_markdown(slug: str) -> str:
    errors: list[str] = []

    if POWERSHELL:
        try:
            return normalize_content(fetch_markdown_via_powershell(slug), slug)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))

    try:
        return normalize_content(fetch_markdown_via_edge(slug), slug)
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))

    raise RuntimeError(" | ".join(errors))


def write_markdown(slug: str, content: str) -> Path:
    target = DESIGN_ROOT / slug / "DESIGN.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch DESIGN.md files from getdesign.md using Windows PowerShell")
    parser.add_argument("slugs", nargs="*", help="Optional subset of slugs to fetch")
    parser.add_argument("--force", action="store_true", help="Refetch even when local DESIGN.md already exists")
    args = parser.parse_args()

    if not POWERSHELL and not EDGE.exists():
        raise SystemExit("Missing both powershell.exe and Windows Edge. This fetcher requires at least one Windows-side fetch path.")

    entries = parse_catalog()
    allowed = set(args.slugs)
    if allowed:
        by_slug = {slug: (slug, name) for slug, name in entries}
        entries = [by_slug[slug] for slug in args.slugs if slug in by_slug]
        for slug in args.slugs:
            if slug not in by_slug:
                entries.append((slug, slug))

    if not entries:
        raise SystemExit("No matching catalog entries to fetch")

    ok = 0
    skipped = 0
    failed: list[tuple[str, str]] = []

    for slug, name in entries:
        target = DESIGN_ROOT / slug / "DESIGN.md"
        if target.exists() and not args.force:
            skipped += 1
            print(f"SKIP {slug:<16} -> {target}")
            continue

        try:
            content = fetch_markdown(slug)
            path = write_markdown(slug, content)
            ok += 1
            print(f"OK  {slug:<16} -> {path}")
        except Exception as exc:  # noqa: BLE001
            failed.append((slug, str(exc)))
            print(f"ERR {slug:<16} -> {exc}")

    print(f"Fetched {ok}/{len(entries)} DESIGN.md files")
    if skipped:
        print(f"Skipped {skipped} existing DESIGN.md files")
    if failed:
        print("Failures:")
        for slug, error in failed:
            print(f"- {slug}: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
