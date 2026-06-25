# MCP Tools Reference

Bear 2.8+ bundles an MCP server (`bearcli mcp-server`) that speaks JSON-RPC 2.0 over stdio. All CRUD operations are available as structured tool calls — no CLI parsing, no silent failures, mandatory optimistic concurrency on overwrites.

## Setup: Global MCP Configuration

Configure once, available in all projects. The server reads/writes the local Bear database in place — no network traffic.

**Claude Code** — add to `~/.claude.json`:

```json
"mcpServers": {
  "bear": {
    "command": "bearcli",
    "args": ["mcp-server"]
  }
}
```

**Claude Desktop** — `~/Library/Application Support/Claude/claude_desktop_config.json`

**Other MCP clients** — configure a stdio server with command `bearcli` and args `["mcp-server"]`.

After configuration, restart the client. 25 MCP tools become available covering create, read, update, delete, search, tags, pins, and attachments.

## Tool Quick Reference

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `search_notes` | Search with Bear syntax | `query`, `limit`, `sort`, `includeContent` |
| `list_notes` | List without query | `tag`, `limit`, `sort`, `location` |
| `create_note` | Create a note | `title`, `content`, `tags`, `ifNotExists` |
| `get_note` | Get metadata | `id`/`title`, `includeContent` |
| `read_note_content` | Get raw body | `id`/`title`, `offset`, `limit` |
| `edit_note` | Atomic partial edit | `id`, `edits` (array, all-or-nothing) |
| `overwrite_note` | Full content replace | `id`, `content`, **`baseHash` (required)** |
| `append_to_note` | Add content | `id`, `content`, `position` |
| `add_tags` | Add tags | `id`, `tags` (⚠️ modifies body — avoid, use Tag Protocol) |
| `remove_tags` | Remove tags | `id`, `tags` (⚠️ modifies body — avoid, use Tag Protocol) |
| `rename_tag` | Rename globally | `old`, `new`, `force` |
| `delete_tag` | Delete from all notes | `tag` |
| `trash_note` | Soft-delete | `id`/`title` |
| `archive_note` | Move to archive | `id`/`title` |
| `restore_note` | Restore from trash/archive | `id`/`title` |
| `open_note` | Open in Bear app | `id`/`title`, `edit`, `newWindow`, `header` |
| `search_in_note` | Find text within a note | `id`, `string`, `context` |
| `list_tags` | List all tags or per-note | `id` (optional) |
| `list_pins` | List pins | `id` (optional) |
| `add_pins` / `remove_pins` | Manage pins | `id`, `targets` |
| `list_attachments` | List note attachments | `id`/`title` |
| `read_attachment` | Get attachment bytes | `id`, `filename` |
| `delete_attachment` | Remove attachment | `id`, `filename` |

## Known Issues (Verified 2026-05-29)

**Tag tools modify body.** `add_tags`, `remove_tags`, `rename_tag`, `delete_tag` all modify the note body — they are not metadata-only. Use the [Tag Operation Protocol](../SKILL.md#tag-operation-protocol) instead.

**`read_note_content` offset/limit returns empty** with offset values 0 or 1. Full reads (no offset/limit) work correctly.

**`create_note` tags param places tags at bottom.** Bear's user setting controls placement. Use `content` to guarantee line-2 positioning.

**iCloud sync conflict badge persists after editing.** When a note carries a conflict marker but has no duplicate, editing the content may not clear it. Fix: `archive_note` → `restore_note`. The location change triggers a full metadata refresh that clears the stale conflict state. (Verified on a 21-attachment note.)
