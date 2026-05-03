# OpenCode-json

This repository tracks portable OpenCode runtime assets, bundled skills,
plugins, and local MCP helpers. Machine-local configuration and runtime state
are intentionally kept out of git.

## Tracked content

- `skills/`: local skills used by OpenCode
- `plugins/`: local plugin scripts and related tests
- `mcp/`: local MCP helpers and integration code
- `package.json` and `package-lock.json`: dependency manifests for local tooling

## Ignored runtime data

The repository does not track runtime-only files such as logs, caches, sqlite
databases, local state snapshots, or machine-local OpenCode config files such as
`opencode.json` and `dcp.jsonc`.

## Local setup

1. Install dependencies with `npm install`.
2. Create or update `opencode.json` locally with the providers and MCP servers
   for the current machine.
3. Do not commit local credentials, API endpoints, sqlite databases, logs, or
   generated runtime state.
