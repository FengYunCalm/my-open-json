# Test Command Patterns

Use the smallest command that matches the user's goal.

## Python / pytest

Prefer this order:
- Repo-native command from project docs or scripts
- `uv run --with pytest python -m pytest ...` when `uv` is available and the repo is not already in an activated env
- `./.venv/bin/pytest ...` when the repo keeps a local virtualenv
- `python -m pytest ...`
- Bare `pytest ...` only when it is already available globally

## JavaScript / TypeScript

Prefer this order:
- Repo-native package script such as `npm test -- ...`, `pnpm test`, or `yarn test`
- Local runner such as `npx vitest run ...` or `npm exec jest -- ...`
- Bare global command only when clearly available

## Go

- Package: `go test ./pkg/...`
- Targeted test: `go test ./... -run TestName`

## Rust

- All tests: `cargo test`
- Targeted test: `cargo test test_name`

## Notes

- Prefer targeted runs before full-suite runs when diagnosing failures.
- Use broader coverage or performance commands only when the user actually asks for them.
- If the expected tool is missing, say so explicitly and provide the next best local command rather than pretending the test actually ran.
