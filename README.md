# OpenCode-json

This repository tracks a portable OpenCode configuration, bundled skills, plugins,
and local MCP helpers.

## Tracked content

- `opencode.json`: checked-in config template with a placeholder API key
- `skills/`: local skills used by OpenCode
- `plugins/`: local plugin scripts and related tests
- `mcp/`: local MCP helpers and integration code
- `package.json` and `package-lock.json`: dependency manifests for local tooling

## Ignored runtime data

The repository does not track runtime-only files such as logs, caches, sqlite
databases, and local state snapshots.

## Local setup

1. Install dependencies with `npm install`.
2. Replace `provider.openai.options.apiKey` in `opencode.json` locally.
3. Keep the checked-in `opencode.json` on the placeholder value when pushing.
