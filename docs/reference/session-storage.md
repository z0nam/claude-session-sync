# Local session storage

> **Reference only.** This document is not part of the launcher toolkit that
> this repo ships. It is a one-time inspection record of how Claude Code
> persists conversations locally, kept because the structure is otherwise
> undocumented and the file inspection that produced this is not free to
> redo. See [`CLAUDE.md`](../../CLAUDE.md) for why this repo deliberately
> does **not** build a sync tool on top of these files.

Derived from inspecting real `.jsonl` files in `~/.claude/projects/` (CLI version `2.1.133`, model `claude-opus-4-7`, observed 2026-05-08).

## Path layout

```
~/.claude/
├── projects/
│   └── <encoded-project-path>/
│       ├── <session-id>.jsonl
│       └── <session-id>/              # sidecar dir (e.g. for "memory" subdir)
├── sessions/
├── backups/
├── file-history/
├── shell-snapshots/
├── session-env/
├── cache/
├── plugins/
├── ide/
├── history.jsonl
└── settings.json
```

### Project path encoding

The `<encoded-project-path>` directory name is the project's absolute path with `/` replaced by `-`.

| Project absolute path        | Encoded directory name        |
|------------------------------|-------------------------------|
| `/Users/namun/dev/Namun_Cho_CV` | `-Users-namun-dev-Namun-Cho-CV` |

Underscores in the original path are preserved; only `/` is rewritten. The leading `-` comes from the leading `/`. Worktrees get their own encoded entry; e.g. `/Users/namun/dev/claude-session-sync/.claude/worktrees/foo` → `-Users-namun-dev-claude-session-sync--claude-worktrees-foo` (the `/.` becomes `--`).

**Caveat:** the encoding is lossy. `/foo-bar/baz` and `/foo/bar/baz` both encode to `-foo-bar-baz`. To recover the true `cwd` for a session, read it from the `cwd` field on any `user`/`assistant` line — do not try to invert the encoding.

## JSONL line schema

One JSON object per line. Lines are appended in chronological order. There is no top-level session record — session-wide metadata (`sessionId`, `cwd`, `gitBranch`, CLI `version`) is repeated on every conversational line.

### Line types observed

Counts from one 415-line session:

| `type`                  | Count | Purpose |
|-------------------------|-------|---------|
| `assistant`             | 181   | Assistant turn (text / thinking / tool_use blocks) |
| `user`                  | 128   | User turn — real input OR `tool_result` payloads |
| `ai-title`              | 36    | Auto-generated session title; latest occurrence wins |
| `last-prompt`           | 34    | Pointer to most recent user prompt + leaf uuid |
| `attachment`            | 18    | Sidecar payloads (system reminders, hooks, MCP info, etc.) |
| `file-history-snapshot` | 10    | Tracked-file backup snapshots keyed by message id |
| `queue-operation`       | 8     | Internal queue events (`enqueue`/`dequeue`/`remove`) |

### Common envelope (on `user`, `assistant`, `attachment`)

```json
{
  "uuid": "<line uuid>",
  "parentUuid": "<prev line uuid or null>",
  "sessionId": "<session uuid, matches filename>",
  "timestamp": "2026-05-08T06:14:29.582Z",
  "cwd": "/Users/namun/dev/Namun_Cho_CV",
  "gitBranch": "main",
  "version": "2.1.133",
  "userType": "external",
  "isSidechain": false,
  "entrypoint": "..."
}
```

`parentUuid` forms a singly-linked list — the conversation is linear, not a tree (sidechains aside). Re-parenting / branching has not been observed in normal sessions.

### `assistant` line

```json
{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "id": "msg_...",
    "model": "claude-opus-4-7",
    "type": "message",
    "stop_reason": "end_turn" | "tool_use",
    "stop_sequence": null,
    "stop_details": {...},
    "content": [
      {"type": "text", "text": "..."},
      {"type": "thinking", "thinking": "..."},
      {"type": "tool_use", "id": "toolu_...", "name": "Bash", "input": {...}}
    ],
    "usage": {
      "input_tokens": 6,
      "output_tokens": 531,
      "cache_creation_input_tokens": 10481,
      "cache_read_input_tokens": 16569,
      "cache_creation": {"ephemeral_5m_input_tokens": 0, "ephemeral_1h_input_tokens": 10481},
      "server_tool_use": {"web_search_requests": 0, "web_fetch_requests": 0},
      "service_tier": "standard",
      "speed": "standard",
      "iterations": [...]
    }
  },
  "requestId": "req_..."
}
```

Content block types observed: `text`, `thinking`, `tool_use`. The full Anthropic API content-block vocabulary applies (so `tool_result` and `image` could in principle appear here too, but in practice `tool_result` shows up on `user` lines).

### `user` line

Three flavors, distinguished by content shape and extra envelope fields:

1. **Real user input** — `message.content` is an array with `text` (and sometimes `image`) blocks.
2. **Tool result** — `message.content[]` contains `tool_result` blocks. Carries an extra top-level `sourceToolAssistantUUID` pointing back to the assistant line whose `tool_use` this answers. Also present: `toolUseResult` (raw tool output, structured).
3. **Meta / system-injected** — `isMeta: true` flag. Used for things like IDE-opened files, image attachments synthesized by the harness. Skip when reconstructing user-authored prompts.

Permission-mode changes show up as `user` lines with a `permissionMode` envelope field.

### `attachment` line

Loosely-typed sidecar. The shape of `attachment` varies — observed `attachment.type` discriminator values include things like:

- `{addedLines, addedNames, removedNames, readdedNames, pendingMcpServers}` — MCP/skills delta
- `{commandMode, prompt, source_uuid}` — slash-command invocation record
- `{content, hookEvent, hookName, toolUseID}` — hook output
- `{content, isInitial, skillCount}` — skills bootstrap
- `{content, itemCount}` — list-style payload
- `{reminderType}` — system reminder

Treat the inner `attachment` object as opaque-but-structured; key off its `type` discriminator.

### `file-history-snapshot` line

```json
{
  "type": "file-history-snapshot",
  "isSnapshotUpdate": false,
  "messageId": "<uuid of the line this snapshot is tied to>",
  "snapshot": {
    "messageId": "...",
    "timestamp": "...",
    "trackedFileBackups": [".gitignore", ...]   // can be [] or list of paths
  }
}
```

These are checkpoints used by Claude Code's internal undo/restore. Backup contents themselves live under `~/.claude/file-history/`, not inline.

### `queue-operation` line

Internal request-queue bookkeeping. Minimal: `{type, operation, timestamp, sessionId}` where `operation ∈ {enqueue, dequeue, remove}`. Safe to drop from any human-facing export.

### `ai-title` and `last-prompt` lines

Both lack the conversational envelope (no `uuid`, `parentUuid`, `cwd` etc.) — they're flat metadata records appended over time.

```json
{"type": "ai-title", "aiTitle": "Update CV GitHub with research papers and reports", "sessionId": "..."}
{"type": "last-prompt", "lastPrompt": "...", "leafUuid": "<latest leaf uuid>", "sessionId": "..."}
```

When extracting "the title" of a session, use the **last** `ai-title` line in the file.

## Implications for export / sync

- **Reconstructing a transcript** = walk lines with `type ∈ {user, assistant}` in file order, follow `parentUuid` for sanity-checking continuity, drop `isMeta:true` user lines unless preserving full fidelity.
- **Tool call/result pairing** = match `tool_use.id` on assistant lines to `tool_result.tool_use_id` on the next non-meta user line (or use `sourceToolAssistantUUID` as a back-pointer).
- **Session metadata** = take the latest `ai-title`, the `sessionId`/`cwd`/`gitBranch`/`version` from any conversational line, and timestamps from the first/last conversational lines.
- **Privacy / size**:
  - `tool_result` content can include full file contents, command output, secrets — must be reviewed/filterable before pushing to any remote.
  - `image` content blocks embed base64 payloads (can be large). A 415-line session was 2.7 MB; this is dominated by tool results and inline images.
  - `usage` blocks contain no secrets but bloat the file; safe to drop in a markdown export.
- **Don't include** `~/.claude/settings.json`, `~/.claude/history.jsonl` (cross-project shell history), `~/.claude/cache/`, or `~/.claude/session-env/` in any export — they contain global state and potentially secrets.

## Other top-level directories

- `~/.claude/sessions/` — present but role unclear; not the primary transcript store.
- `~/.claude/backups/` — auto-snapshots; retention unverified.
- `~/.claude/file-history/` — backing store for `file-history-snapshot` entries.
- `~/.claude/shell-snapshots/` — captures of shell state for the Bash tool.
- `~/.claude/session-env/` — per-session env vars; treat as secret.
- `~/.claude/cache/` — transient.
- `~/.claude/plugins/` — installed plugins.
- `~/.claude/ide/` — IDE-extension state.
- `~/.claude/history.jsonl` — global prompt history across all projects.
- `~/.claude/settings.json` — global settings (hooks, permissions, env). **Never** export.
