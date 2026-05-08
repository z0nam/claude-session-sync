# Context for future Claude sessions

This file captures the conversation that motivated this project so a future Claude session can pick up cold.

## Origin

The project was started during a Claude Code on the web session that was working on an unrelated repo (`z0nam/Namun_Cho_CV`). The user noticed:

1. Sessions running locally in VS Code (Claude Code extension) were **not visible** from the web environment.
2. Sessions started in the Claude Code desktop app **were visible** in the local VS Code extension.
3. They wanted to know how to make all sessions visible everywhere.

## What we established

- Local Claude Code surfaces (VS Code extension, desktop app, terminal CLI) all read/write the same on-disk store: `~/.claude/projects/<encoded-project-path>/*.jsonl`. The encoding replaces `/` in the absolute project path with `-` (e.g. `/home/user/Namun_Cho_CV` → `-home-user-Namun-Cho-CV`).
- The web environment (`claude.ai/code`) runs in a fresh Anthropic-managed sandbox VM. Its session storage is in the cloud and is not reachable from the user's machine.
- Therefore: local-to-local sharing is automatic; local-to-web (or web-to-local) sharing is **not supported by Claude Code today**.
- There is no built-in setting or CLI flag to enable cross-environment sync. This is an architectural gap, not a configuration issue.

## Why a separate project

The Namun_Cho_CV repo is a personal CV; mixing a tooling experiment into it would be off-topic. The user asked to spin this off into its own project, develop a real sync tool, and preserve the above context so the next session does not have to re-derive it.

## Constraints observed during bootstrap

- The web session's GitHub MCP scope was originally limited to `z0nam/namun_cho_cv`. The user manually created `git@github.com:z0nam/claude-session-sync.git` and provided the URL; the bootstrap commit was pushed to that remote.

## What to do next

When picking this project up:

1. Inspect a real `~/.claude/projects/<encoded-path>/*.jsonl` file and document its line schema in `docs/session-storage.md`.
2. Decide an export format (markdown for readability vs. JSON for fidelity — likely both, with markdown as the default surface).
3. Decide a sync target. The leading candidate is a user-owned GitHub repo (private), since the user can `git clone` it from a web sandbox to restore context.
4. Sketch the CLI: at minimum `claude-sync export <session-id|--all>` and `claude-sync push`.

Do not assume any cloud-side API for web sessions exists; if you discover one, document it before relying on it.
