---
name: awesome-design
description: Use when the user wants a page, component, or product UI to feel like a known site or brand, or gives aesthetic adjectives and needs you to choose the closest reference from the bundled awesome-design-md catalog before implementation.
allowed-tools:
  - bash
  - glob
  - grep
  - read
  - webfetch
---

# Awesome Design

This skill helps map a visual request to a concrete reference from the awesome-design-md collection. The upstream repository snapshot is vendored under `references/upstream/`, so the agent can search locally first instead of depending on an external clone path.

## Local Sources

- `scripts/match_reference.py`: local matcher that ranks the best references for a user prompt
- `references/upstream/design-md/<slug>/DESIGN.md`: local full design document when fetched and cached
- `references/matching-cues.md`: fastest route for vibe-first requests
- `references/catalog.md`: normalized name, slug, URL, and one-line summary catalog
- `references/upstream/README.md`: authoritative upstream collection index and category source
- `references/upstream/design-md/<slug>/README.md`: per-site local stub that confirms the target design URL

## When to Use

Use this skill when the user:
- names a brand or site style directly, such as `like Vercel`, `use a Claude-like look`, or `make it feel like Notion`
- describes a vibe and wants you to pick a fitting design reference, such as `warm editorial`, `dark developer-tool aesthetic`, or `monochrome minimal`
- wants design inspiration or a style source before implementing or restyling a frontend surface

## Boundaries

- Do not use for generic UI implementation when no reference selection is needed.
- Once a reference has been chosen, continue the work and preserve the host project's existing design language unless the user explicitly asked for a stronger restyle.
- Do not use for fixed brand-compliance work where the brand system is already known.

## Workflow

1. Parse the request across four axes: domain, tone, density, and standout cues.
2. Run `python3 scripts/match_reference.py "<user request>" --top 3` from this skill directory to get a first-pass ranking.
3. For adjective-led prompts, use `references/matching-cues.md` to sanity-check the matcher output, especially for Chinese prompts or short vibe descriptions.
4. Search `references/upstream/README.md` and `references/catalog.md` locally only when the matcher output is ambiguous or clearly weak.
5. If `references/upstream/design-md/<slug>/DESIGN.md` exists, read it directly and use it as the source of truth.
6. Otherwise inspect the matching stub at `references/upstream/design-md/<slug>/README.md` to confirm the target URL.
7. Pick 1 primary reference and at most 2 alternates. Explain the fit in plain language.
8. If the full local `DESIGN.md` is missing and external fetch works, open the reference URL from the catalog or stub. If fetch fails, continue with the local summary and clearly say the remote doc could not be fetched.
9. For implementation tasks, carry the chosen reference into the solution without replacing an existing project design system unless the user asked for that change.

## Matching Rules

- Prefer exact brand or slug matches over vibe matching.
- If the user is asking for a docs, SaaS, IDE, fintech, or AI product surface, bias toward the same domain first.
- Use the short catalog summaries as the first filter: `editorial`, `cinematic`, `terminal`, `dashboard`, `minimal`, `gradient`, `monochrome`, `dense`, `friendly`, `developer`, `photography`, `technical`.
- If several entries fit, prefer the one whose summary most directly matches the user's requested tone and component type.
- If the user names a known brand and also gives style adjectives, keep the named brand as primary unless the adjectives clearly contradict it.
- If nothing is a clean match, say that and offer the closest 2 options instead of pretending certainty.

## Notes

- `references/upstream/` contains the vendored upstream README and per-site redirect stubs, which are the authoritative local source for site names and URLs.
- `references/catalog.md` is a normalized summary layer extracted from the upstream collection and is the fastest offline search surface.
- `references/matching-cues.md` is intentionally opinionated and exists to improve adjective-to-reference matching speed. Use it as a starting point, not as a hard rule.
- `scripts/rebuild_catalog.py` also backfills missing local stubs for catalog entries, so the skill keeps working even when the vendored upstream snapshot is incomplete.
- `scripts/fetch_design_docs.py` can batch-fetch and cache the real upstream `DESIGN.md` files into the local skill directory through Windows-side fetch paths (PowerShell first, Edge headless fallback). It defaults to filling missing local docs and skips existing files unless explicitly forced. Treat it as Windows/WSL-specific, not a portable Linux fetch path.
- Some upstream site folders are only redirect stubs, so local matching should happen against the vendored README and catalog first rather than assuming a real local `DESIGN.md` exists.
- When external fetch is unavailable, still provide the best local match, the design URL, and the cues you would apply.

## Output Format

```markdown
## Awesome Design Match

**Primary reference:**
**Why it fits:**
**Alternate references:**
**Design cues to apply:**
**Local docs used:**
**Source URL:**
**Fetch status:**
```

## Related Skills

- Use `frontend-design` when the task moves from reference selection into actual UI implementation.
