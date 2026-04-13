---
name: ui-ux-pro-max
description: Use when UI work needs structured guidance for visual style, color palette, typography, landing-page pattern, accessibility review, chart choice, or stack-specific frontend recommendations across web and app interfaces.
license: MIT
metadata:
  author: NextLevelBuilder
  adapted_for: OpenCode
  adapted_by: OpenCode
  version: "2.5.0-opencode"
---

# UI UX Pro Max

## Local Integration Note

- This is an OpenCode-adapted version of the upstream skill, trimmed to fit the local global skill workflow.
- It does not modify global `AGENTS.md`, does not install project-local `.opencode` files, and does not replace existing process skills.
- For React or Next.js implementation, combine this skill with `vercel-react-best-practices`.
- For React component API and composition design, combine this skill with `vercel-composition-patterns`.

## Overview

Use this skill when a task needs design intelligence rather than generic taste: style selection, color systems, typography pairing, landing-page structure, UX rule lookup, chart selection, or stack-aware UI guidance.

The core value is the bundled searchable dataset and design-system generator in `scripts/search.py`.

## When to Use

Use this skill when the task involves:

- Designing or restyling a landing page, dashboard, admin panel, marketing page, mobile UI, or design system
- Choosing visual direction for a product such as fintech, SaaS, healthcare, e-commerce, AI, portfolio, or content apps
- Picking or validating color palettes, font pairings, motion style, responsive layout direction, or chart types
- Reviewing an existing UI for professionalism, consistency, accessibility, interaction quality, or visual hierarchy
- Needing structured recommendations instead of ad-hoc design opinions

Do not use this skill for:

- Backend-only work
- API, database, infra, or DevOps tasks
- Non-visual bugfixes
- Cases where implementation details matter more than design direction and an existing domain skill already covers it better

## Workflow

1. Extract the request dimensions: product type, target audience, tone, platform, and any explicit visual constraints.
2. Start with a design-system recommendation.
3. If needed, follow with domain or stack searches.
4. Synthesize the recommendations with the repo's existing design language instead of copying them literally.
5. If code will be written, use the relevant implementation skill after the design direction is clear.

## Commands

Run the bundled script directly:

```bash
python3 ~/.config/opencode/skills/ui-ux-pro-max/scripts/search.py "<query>" --design-system -p "<Project Name>"
```

Examples:

```bash
python3 ~/.config/opencode/skills/ui-ux-pro-max/scripts/search.py "fintech dashboard premium trustworthy" --design-system -p "Ledger Pro"
python3 ~/.config/opencode/skills/ui-ux-pro-max/scripts/search.py "glassmorphism fintech" --domain style
python3 ~/.config/opencode/skills/ui-ux-pro-max/scripts/search.py "error states forms" --domain ux
python3 ~/.config/opencode/skills/ui-ux-pro-max/scripts/search.py "table density filters" --stack react
```

## Domains

Use `--domain <name>` for targeted lookup.

| Domain | Use For |
|--------|---------|
| `product` | Product-specific visual recommendations |
| `style` | UI style families and effects |
| `color` | Industry/product color systems |
| `typography` | Font pairings |
| `google-fonts` | Font family lookup |
| `landing` | Landing-page pattern and CTA structure |
| `chart` | Visualization choice |
| `ux` | UX and accessibility rules |
| `icons` | Icon library and usage suggestions |
| `react` | React/Next performance-oriented UI guidance |
| `web` | Web/app interface guidance |

## Stacks

Use `--stack <name>` for implementation guidance.

Available stacks include:

`react`, `nextjs`, `vue`, `nuxtjs`, `nuxt-ui`, `svelte`, `astro`, `html-tailwind`, `shadcn`, `angular`, `laravel`, `swiftui`, `react-native`, `flutter`, `jetpack-compose`, `threejs`

## Practical Rules

- Start with `--design-system` before debating individual colors or fonts.
- Treat generated output as a recommendation set, not a mandate.
- If the repo already has an established design system, adapt the output to that system instead of replacing it.
- For React and Next.js code, do not use this skill as a substitute for `vercel-react-best-practices`.
- For component architecture choices, do not use this skill as a substitute for `vercel-composition-patterns`.

## Common Mistakes

- Picking a style first and only later checking product fit
- Copying a suggested palette without validating contrast and semantic color roles
- Using this skill for backend or non-visual work
- Treating the generated design system as permission to ignore the current project's visual language
- Jumping into code before establishing the visual direction when the task is clearly UI-led

## Output Tips

- `--design-system` is best for initial direction.
- `-f markdown` is better when you want to paste the result into docs or a spec.
- `--persist` can write a design-system folder in the current project, but only use it when the user explicitly wants project files created.

## Bundled Assets

- Script entry: `scripts/search.py`
- Search engine: `scripts/core.py`
- Design-system generator: `scripts/design_system.py`
- Data source: `data/*.csv`
