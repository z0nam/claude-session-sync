# claude-session-sync

A tiny operator's toolkit for **Claude Code Remote Control**: a launcher and
long-running service unit so your laptop's Claude Code session is always
reachable from the Claude mobile app or `claude.ai/code` in a browser.

> Project history note: this repo was originally scoped as a local↔web session
> *file* sync tool, on the assumption that no such bridge existed. Anthropic
> shipped **Remote Control** (Claude Code v2.1.51+), which already provides the
> bridge — your local session keeps running on your machine and is driven from
> any device. So the project pivoted: instead of reinventing it, this repo
> wraps and operationalises it. See `CLAUDE.md` for the full backstory.

## What this gives you

- **`bin/claude-remote`** — a wrapper around `claude remote-control` that
  - checks `claude` is installed and recent enough (≥ 2.1.51),
  - auto-derives a session name from `hostname` + project dir,
  - optionally sources `~/.config/claude-remote.env` for defaults,
  - forwards every other flag straight through to `claude remote-control`.
- **`systemd/claude-remote.service`** — a user-scope systemd unit so the
  Remote Control server starts at login on Linux and restarts on failure.
- **`launchd/com.anthropic.claude-remote.plist`** — equivalent LaunchAgent
  for macOS.
- **`docs/setup.md`** — copy-paste install steps for both platforms.

## Quick start

```bash
# 1. Put the launcher on your PATH
install -m 0755 bin/claude-remote ~/.local/bin/claude-remote

# 2. (Optional) set defaults
mkdir -p ~/.config
cp systemd/claude-remote.env.example ~/.config/claude-remote.env
$EDITOR ~/.config/claude-remote.env   # set CLAUDE_REMOTE_DIR, etc.

# 3. Try it in the foreground first
claude-remote

# 4. When happy, enable the background service (Linux)
mkdir -p ~/.config/systemd/user
cp systemd/claude-remote.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now claude-remote.service
```

macOS instructions and troubleshooting live in [`docs/setup.md`](docs/setup.md).

## What this is *not*

- Not a re-implementation of Remote Control. It calls the official
  `claude remote-control` subcommand and only adds glue.
- Not a session-history sync. Past conversations still live in
  `~/.claude/projects/*.jsonl` on the host that ran them; this tool does not
  ship them anywhere. If you need a particular conversation visible elsewhere,
  use Remote Control to keep that session live, or copy the JSONL yourself.
- Not a tunnel or inbound listener. Remote Control's transport is outbound
  HTTPS to the Anthropic API; this repo doesn't change that.

## Status

Early. The launcher and service units are intended to be small enough to
audit in one sitting. PRs welcome.
