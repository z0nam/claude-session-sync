# Setup

End-to-end install for the `claude-remote` launcher and its background
service unit. Pick the section for your OS.

## Prerequisites

- `claude` (Claude Code CLI) version **2.1.51 or newer**. Check with
  `claude --version`.
- A signed-in claude.ai account (`claude` then `/login`). Remote Control
  does **not** work with `ANTHROPIC_API_KEY` or long-lived setup tokens.
- Workspace trust accepted at least once in your project directory.

If you are on a Team or Enterprise plan, an admin also needs to flip the
**Remote Control** toggle in
[claude.ai/admin-settings/claude-code](https://claude.ai/admin-settings/claude-code).

## Linux

```bash
# 1. Install the launcher onto PATH
install -m 0755 bin/claude-remote ~/.local/bin/claude-remote

# 2. Configure defaults (optional but recommended for the service)
mkdir -p ~/.config
cp systemd/claude-remote.env.example ~/.config/claude-remote.env
$EDITOR ~/.config/claude-remote.env   # set CLAUDE_REMOTE_DIR

# 3. Smoke-test in the foreground
~/.local/bin/claude-remote
# Press Ctrl+C once you've confirmed the session URL appears.

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
$EDITOR ~/.config/claude-remote.env

# 3. Smoke-test in the foreground
~/.local/bin/claude-remote

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
- **Service flapping (`Restart=on-failure` keeps firing)** — run the
  launcher manually to see the real error. The most common causes are
  missing/expired login (`/login` again) and `CLAUDE_REMOTE_DIR` pointing
  at a path that doesn't exist.
- **No session in claude.ai/code** — confirm with `systemctl --user status
  claude-remote` (Linux) or `launchctl list | grep claude-remote` (macOS).
  Then check the journal/log for the session URL line; if it's there, the
  problem is the browser side (wrong account, etc.), not the daemon.
