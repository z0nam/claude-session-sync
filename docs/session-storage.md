# Local session storage

Notes on how Claude Code persists conversations on the local filesystem. To be expanded as we actually parse files.

## Path layout

```
~/.claude/
├── projects/
│   └── <encoded-project-path>/
│       └── <session-id>.jsonl
├── sessions/
├── backups/
├── shell-snapshots/
├── settings.json
└── ...
```

### Encoding rule

The `<encoded-project-path>` directory name is the project's absolute path with `/` replaced by `-`.

Observed example (from the sandbox where this project was bootstrapped):

| Project absolute path     | Encoded directory name        |
|---------------------------|-------------------------------|
| `/home/user/Namun_Cho_CV` | `-home-user-Namun-Cho-CV`     |

Note that underscores in the original path are preserved; only `/` is rewritten. The leading `-` comes from the leading `/` of the absolute path.

## JSONL line schema

**TODO** — read an actual session file and document the per-line structure (likely one JSON object per turn or per event, with role/content/tool-use fields). Fill this in before writing the parser.

## Other directories

- `~/.claude/sessions/` — purpose unconfirmed; inspect.
- `~/.claude/backups/` — likely auto-snapshots; inspect retention policy.
- `~/.claude/shell-snapshots/` — likely captures of shell state when Bash tool ran; check size/retention before treating as part of session export.
- `~/.claude/settings.json` — user/global Claude Code settings (hooks, permissions, env). Do **not** include in any export.
