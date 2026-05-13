# Setup

End-to-end install for the `claude-remote` launcher and its background
service unit. Pick the section for your OS.

## Prerequisites

- `claude` (Claude Code CLI) version **2.1.51 or newer**. Check with
  `claude --version`.
- A signed-in claude.ai account (`claude` then `/login`). Remote Control
  does **not** work with `ANTHROPIC_API_KEY` or long-lived setup tokens.
- Workspace trust accepted at least once in your project directory
  (just run `claude` there and accept the dialog).
- **First-run consent for `claude remote-control` — see the next section.**
  Service units cannot complete this; it must be done by hand once.

If you are on a Team or Enterprise plan, an admin also needs to flip the
**Remote Control** toggle in
[claude.ai/admin-settings/claude-code](https://claude.ai/admin-settings/claude-code).

## First-run consent (do this once, by hand)

The first time `claude remote-control` runs in a project directory, it
shows **two interactive prompts** before opening the server. Both require
stdin, so a launchd / systemd unit will hang on them. There is no
non-interactive flag to skip them — confirmed against `claude remote-control --help`.

So before installing the service unit, run the launcher in a real
terminal once:

```bash
cd <your-project-dir>
~/.local/bin/claude-remote      # or bin/claude-remote from this repo
```

You will be asked:

1. **`Enable Remote Control? (y/n)`** — answer `y`. This is a
   one-time, account-wide consent and is remembered permanently.
2. **`Spawn mode for this project: [1] same-dir [2] worktree`** — pick
   `1` for shared cwd (most users want this) or `2` for an isolated git
   worktree per session. The choice is saved **per project** in
   `~/.claude.json` (`remoteControlSpawnMode`). You can change it later
   with the `--spawn=...` flag or by pressing `w` while the server runs.

Once you see the "Connected" banner with the session URL, press
<kbd>Ctrl</kbd>+<kbd>C</kbd> to exit. Re-running the launcher should now
go straight into the server with no prompts.

## Optional: global auto-enable for interactive sessions

Inside any `claude` session, run `/config` and turn on **Enable Remote
Control for all sessions**. After this, every `claude` session you start
yourself (in any directory) auto-registers with Remote Control — no need
to type `/remote-control` each time. The toggle is persisted as
`"remoteControlAtStartup": true` in `~/.claude/settings.json`.

This only covers sessions **you** start. It does **not** keep a server
running in the background for projects you are not actively in — that is
what the launchd / systemd unit below is for. The two are complementary.

## Linux

```bash
# 1. Install the launcher onto PATH
install -m 0755 bin/claude-remote ~/.local/bin/claude-remote

# 2. Configure defaults (optional but recommended for the service)
mkdir -p ~/.config
cp systemd/claude-remote.env.example ~/.config/claude-remote.env
$EDITOR ~/.config/claude-remote.env   # set CLAUDE_REMOTE_DIR

# 3. Run the first-run consent step above in CLAUDE_REMOTE_DIR.

# 4. Install + enable the user service
mkdir -p ~/.config/systemd/user
cp systemd/claude-remote.service ~/.config/systemd/user/claude-remote.service
systemctl --user daemon-reload
systemctl --user enable --now claude-remote.service

# 5. Confirm
systemctl --user status claude-remote.service
journalctl --user -u claude-remote.service -f
```

Optionally enable lingering so the service survives logout:

```bash
loginctl enable-linger "$USER"
```

### Uninstall (Linux)

```bash
systemctl --user disable --now claude-remote.service
rm ~/.config/systemd/user/claude-remote.service
systemctl --user daemon-reload
rm ~/.local/bin/claude-remote ~/.config/claude-remote.env
```

## macOS

```bash
# 1. Install the launcher
install -m 0755 bin/claude-remote ~/.local/bin/claude-remote

# 2. Configure defaults
mkdir -p ~/.config
cp systemd/claude-remote.env.example ~/.config/claude-remote.env
$EDITOR ~/.config/claude-remote.env   # set CLAUDE_REMOTE_DIR

# 3. Run the first-run consent step above in CLAUDE_REMOTE_DIR.

# 4. Materialise the LaunchAgent (LaunchAgents don't expand $HOME, so we
#    substitute your username into the template).
mkdir -p ~/Library/LaunchAgents ~/Library/Logs
sed "s|YOUR_USERNAME|$USER|g" launchd/com.anthropic.claude-remote.plist \
    > ~/Library/LaunchAgents/com.anthropic.claude-remote.plist

# 5. Load it
launchctl load -w ~/Library/LaunchAgents/com.anthropic.claude-remote.plist

# 6. Tail logs to confirm
tail -f ~/Library/Logs/claude-remote.out.log
```

### Uninstall (macOS)

```bash
launchctl unload -w ~/Library/LaunchAgents/com.anthropic.claude-remote.plist
rm ~/Library/LaunchAgents/com.anthropic.claude-remote.plist
rm ~/.local/bin/claude-remote ~/.config/claude-remote.env
```

## Connecting from another device

Once the service is up, open [claude.ai/code](https://claude.ai/code) or the
Claude mobile app and look for the session in the list — Remote Control
sessions show a computer icon with a green status dot. The launcher names
the session `<hostname>-<project-dir>` unless you passed `--name` yourself.

For a QR-code shortcut from your phone, run the launcher in the foreground
once (`claude-remote`) and press <kbd>Space</kbd>; the CLI will render a QR
that points the Claude app at this session.

## Troubleshooting

- **`claude-remote: Remote Control needs claude >= 2.1.51 …`** — upgrade
  the CLI. The version is parsed from the first whitespace-delimited token
  of `claude --version`; if your build emits something unusual, open an
  issue with the exact output.
- **Service unit starts, then exits immediately** — almost always the
  first-run consent step was skipped. Run the launcher manually in
  `CLAUDE_REMOTE_DIR` once, answer the two prompts, then re-enable the
  service.
- **Service flapping (`Restart=on-failure` keeps firing)** — run the
  launcher manually to see the real error. After ruling out the
  first-run consent issue above, the next likely causes are
  missing/expired login (`/login` again) and `CLAUDE_REMOTE_DIR`
  pointing at a path that doesn't exist or isn't workspace-trusted.
- **No session in claude.ai/code** — confirm with `systemctl --user status
  claude-remote` (Linux) or `launchctl list | grep claude-remote` (macOS).
  Then check the journal/log for the session URL line; if it's there, the
  problem is the browser side (wrong account, etc.), not the daemon.
