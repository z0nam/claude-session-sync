# claude-session-sync

Tooling to sync Claude Code sessions across environments — primarily to bridge the gap between local sessions (VS Code extension, desktop app, terminal CLI) and web sessions at `claude.ai/code`.

## Problem

Claude Code stores conversations differently depending on where it runs:

- **Local surfaces** (VS Code extension, desktop app, terminal CLI) all read from `~/.claude/projects/<encoded-project-path>/*.jsonl` on the user's machine. Because they share the same files on the same host, sessions are mutually visible across these surfaces.
- **Web** (`claude.ai/code`) runs in an Anthropic-managed cloud sandbox. Its session storage lives in that VM and is not exposed to the local filesystem.

There is currently no built-in mechanism to view a local session from the web, or vice versa. This project explores what we can build on top of the local JSONL files to close that gap as much as possible.

## Goals

- **v0.1 — export**: Read `~/.claude/projects/*.jsonl` and produce a human-readable export (markdown or structured JSON) of past sessions.
- **v0.2 — push sync**: Push exported sessions to a destination the web environment can read (e.g. a user-owned GitHub repo, gist, or object store). The web session can then `git clone` / fetch to recover prior local context.
- **v0.3 — bidirectional (best effort)**: Capture web session transcripts (whatever the web UI exposes) and merge them back into the local store.

## Non-goals

- Reverse engineering or scraping any private Claude API.
- Cloud-to-local sync of sessions that the web environment does not expose. Without a public API for web session storage, this direction is fundamentally limited.

## Status

Bootstrap only. No implementation yet. See `CLAUDE.md` for the conversation that motivated this project.
