---
name: ai-player
description: Use when working on the XiaKeXing project and you need the xiakexing_ai MCP tools for gameplay automation, regression testing, or maintenance checks in Windows or Ubuntu environments.
license: MIT
compatibility: opencode
---

# AI-Player (XiaKeXing)

## Local Integration Note

This skill is intentionally project-specific.

## When to Use

Use when the task is inside the `XiaKeXing` repository and the session exposes `xiakexing_ai_*` MCP tools for gameplay automation, regression checks, maintenance validation, or controlled in-game command execution.

## Boundaries

- Do not use outside the `XiaKeXing` repository.
- Do not use when the current session does not expose `xiakexing_ai_*` MCP tools.
- Do not use for generic game design, generic test planning, or unrelated MCP workflows.

Use it only when all of the following are true:

- the current task is for the `XiaKeXing` repository
- the session exposes the `xiakexing_ai_*` MCP tools
- the repo-local `tools/ai-player/` directory exists

Do not assume a single fixed absolute path forever. On this machine, the currently known repo roots are:

- Windows: `C:/Users/23916/Desktop/XiaKeXing`
- Ubuntu: `/home/mechrevo/projects/XiaKeXing`

## What This Skill Is For

Use this skill to drive the repo-local ai-player MCP for:

- smoke checks
- regression runs
- maintenance verification
- controlled in-game command execution
- bug reproduction from a real player perspective

MCP registration key: `xiakexing_ai`

Repo-local assets:

- MCP server: `tools/ai-player/mcp_server.py`
- config: `tools/ai-player/config.yaml`
- protocol contract: `tools/ai-player/PROTOCOL_CONTRACT.md`

The ai-player transport layer now supports two modes:

- `tcp` for canonical direct driver validation
- `websocket` for the latest Go gateway path

## Runtime Entry Points

The canonical server config remains:

- `server/config/driver.config`

The canonical driver binary depends on the current environment:

- Windows runtime: `driver/bin/driver.exe`
- Ubuntu runtime: `driver/bin/driver`

If the matching runtime binary does not exist in the active repo tree, stop and report that the repo is not prepared for ai-player use in that environment.

Do not treat `tools/server-manager/IntegratedServerManager.cs` as the canonical startup path.

### Gateway Validation Path

When the goal is to validate the latest Go gateway path instead of the direct TCP path, use the repo-local launchers:

- `tools/start-server-driver-gateway-ubuntu.sh`
- `tools/start-gateway-ubuntu.sh`

Expected gateway chain on Ubuntu:

- WebSocket gateway: `127.0.0.1:8080`
- driver gateway: `127.0.0.1:6040`
- isolated FluffOS runtime: `127.0.0.1:6939`

Repo-local ai-player now supports gateway testing by configuring:

- `server.transport = websocket`
- `server.host = 127.0.0.1`
- `server.port = 8080`
- `server.websocket_path = /`

For direct MCP tool calls, prefer:

- `xiakexing_ai_connect_server(host="127.0.0.1", port=8080, transport="websocket")`

If the tool session still exposes the older schema without `transport`, update/restart the repo-local MCP server before assuming gateway mode is unsupported.

## Typical Workflow

1. Ensure the repo-local driver is running with the repo-local `driver.config`.
2. `xiakexing_ai_connect_server`
3. `xiakexing_ai_login_game`
4. `xiakexing_ai_send_game_command`
5. `xiakexing_ai_get_game_status`
6. `xiakexing_ai_get_bug_report`
7. `xiakexing_ai_disconnect_server`

Stronger test paths:

- `xiakexing_ai_run_regression_test`
- `xiakexing_ai_run_clean_regression_test`
- `xiakexing_ai_run_admin_maintenance_test`

## Preconditions

- The MUD server should be reachable at the host and port configured in `tools/ai-player/config.yaml`.
- Direct mode default remains `localhost:3939`.
- Latest gateway validation mode uses `127.0.0.1:8080` with `server.transport = websocket`.
- Maintenance/report commands are expected to emit the contract described in `tools/ai-player/PROTOCOL_CONTRACT.md`.

## Operating Rules

- Prefer repo-relative paths when explaining or launching anything.
- Before starting a local server, verify which repo tree is active: Windows or Ubuntu.
- When the user only asks for ai-player MCP operations, use the MCP tools directly and do not invent extra startup steps.
- If the tool session does not expose `xiakexing_ai_*`, say that plainly and stop.
- If login or connection appears inconsistent, confirm actual in-game state with `xiakexing_ai_get_game_status` before assuming the failure is real.
- When the task explicitly targets the latest gateway path, prefer websocket transport over falling back to direct TCP.
- When using websocket transport, remember that ai-player is validating the Go gateway chain, not the raw `3939` listener.

## Troubleshooting

- If connection fails, verify the repo-local driver is listening on `localhost:3939`.
- If websocket gateway validation fails, verify `127.0.0.1:8080` is listening and `tools/start-gateway-ubuntu.sh` is using the repo-local `gateway-go/` tree.
- If websocket gateway validation fails but direct TCP works, treat it as a gateway-chain issue first, not a generic ai-player failure.
- If Ubuntu regression is requested but only `driver.exe` exists, stop and report that the Ubuntu runtime has not been installed into this repo tree yet.
- If Windows regression is requested but only Linux binaries exist, stop and report the same mismatch.
- If long-lived sessions behave strangely, disconnect and reconnect before assuming a protocol bug.
