---
name: relay-room
description: Use when the user wants to create, join, message, inspect, or export relay rooms or threads, and the current session exposes relay room tools.
license: MIT
compatibility: opencode
metadata:
  audience: operators
  workflow: room-relay
---

# Relay Room Skill

## Overview

This skill is for real relay side effects: rooms, joins, messages, threads, and transcript export. When the requested action is clear, act through the relay tools first and explain afterward.

## Mode Selection

Use **room mode** for room create, join, status, members, and room-level messaging.

Use **thread mode** for durable thread creation, listing, message history, and read markers.

Use **export mode** for transcript export.

## Workflow

1. Identify the requested relay action.
2. If a required argument is missing, ask only for that missing piece.
3. Call the matching relay tool.
4. Reply with the real result, not a guessed one.

## Output Contract

Report the minimum fields that matter for the completed action, such as:
- `roomCode`
- `alias`
- `threadId`
- member or delivery status
- failure reason when the tool call fails

## Good Habits

- Let the normal session injection handle session identity when the relay plugin supports it.
- Treat this as an execution skill, not an analysis skill.
- Stop cleanly if the relay tools are not exposed in the session.

## Example

User: "Create a group room and give me the code."

Good behavior: call the room-creation tool first, then report the actual room code and owner status.
