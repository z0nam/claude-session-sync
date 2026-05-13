# Context for future Claude sessions

This file captures why this project exists in its current form so a future
Claude session can pick up cold.

## Origin (what we set out to solve)

The repo was created during a Claude Code on the web session. The user had
noticed that:

1. Sessions running locally (VS Code extension, desktop app, terminal CLI)
   were **not visible** from the web environment.
2. Sessions started in the desktop app **were visible** in the local VS Code
   extension (they share `~/.claude/projects/*.jsonl`).
3. The web environment (`claude.ai/code`) runs in an Anthropic-managed cloud
   sandbox, with its own session storage in the cloud and no exposure to the
   user's filesystem.

Original framing: build a tool that exports local JSONL session files and
pushes them somewhere the web sandbox can `git clone` to recover prior
context. See git history for the bootstrap README/docs that reflected that
plan.

## The pivot

Anthropic shipped **Remote Control** in Claude Code v2.1.51 (announced 2026).
Remote Control lets a Claude Code session running locally be **driven** from
`claude.ai/code` or the Claude mobile app:

- The session keeps running on the user's machine — local FS, MCP servers,
  tools, and project config all stay live.
- The web/mobile UI is just a window into that local session.
- Transport is outbound HTTPS only; no inbound listener on the machine.

That solves the user's actual underlying need ("continue my local work from
my phone / a browser") more cleanly than any sync tool could, because no
history has to move. So the repo was redirected: instead of inventing a
sync protocol, this project now ships a thin launcher + a long-running
service unit that makes Remote Control trivial to keep on.

What Remote Control does **not** solve (and this repo deliberately does not
attempt):

- It is not an archive. If the local process exits, the session ends. Past
  JSONL conversations are not browsable from another device.
- It is not bidirectional file sync. Web-only sessions still live in the
  cloud sandbox and are not reachable from the local machine.

If those gaps ever matter, revisit the original sync idea — but build it as
a separate tool, not in this repo.

## Current shape of the repo

- `bin/claude-remote` — bash launcher around `claude remote-control`.
  Sanity-checks the install, picks a sensible default session name, sources
  `~/.config/claude-remote.env` if present, then `exec`s the real subcommand.
- `systemd/claude-remote.service` + `claude-remote.env.example` — Linux user
  unit for keeping it running across reboots.
- `launchd/com.anthropic.claude-remote.plist` — macOS LaunchAgent equivalent.
- `docs/setup.md` — install/uninstall steps.

There is intentionally no daemon code, no client library, no parser. The
official `claude` CLI does all the heavy lifting; this repo is glue.

## Constraints worth remembering

- The launcher should never invent flags. If `claude remote-control` adds or
  renames a flag, users should be able to pass it through without waiting on
  this repo. Pre-flight checks should stay limited to "is the CLI present
  and recent enough"; behaviour is the upstream subcommand's responsibility.
- The systemd unit runs as the user (`systemctl --user`). Do **not** suggest
  a system-wide unit — Remote Control authenticates against a specific
  user's claude.ai login and needs that user's keyring/credentials.
- macOS LaunchAgents go in `~/Library/LaunchAgents`, run as the logged-in
  user, and need `RunAtLoad` + `KeepAlive` to behave like the systemd unit.

## Suggested next steps

1. Validate the launcher against a real `claude --version` output on the
   user's machine and adjust the version-extraction regex if needed. The
   current implementation assumes the first whitespace-delimited token is a
   semver.
2. Decide whether to bundle a `claude-remote status` helper (e.g. parse
   `systemctl --user is-active` and surface the session URL). Out of scope
   for v0.1; worth doing once there is a second use case.
3. Consider a `--dry-run` flag for the launcher that prints the exact
   `claude remote-control` invocation it would run. Cheap to add, helpful
   when debugging service units.

Do not bring back the JSONL-export direction inside this repo. If that need
re-emerges, spin a separate repo so the two concerns do not bleed.
