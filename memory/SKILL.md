---
name: bear-memory
description: Use when the agent needs to store, retrieve, or manage persistent memories. Triggers on: remember, 记忆, recall, 回忆, forget, 忘记, memory, what do you know about me, 你知道我, 之前说过, preferences, 偏好. Depends on bear-notes skill for Bear MCP operations.
---

# Bear Memory

Persistent memory system for AI agents backed by Bear notes. Two-layer storage (index + entries) with semantic search via local embeddings. Follows the CoALA framework (user / feedback / project / reference).

**Prerequisites:**
- bear-notes skill loaded (MCP operations + Tag Protocol)
- `memory/requirements.txt` installed (`pip3 install -r requirements.txt`)
- `embed.py --rebuild` run at least once

## Memory Note Format

### Entry Note (one per memory)

```markdown
# 「MEM」<semantic title>
#ai/memory/<type>/entry

<!-- type: <type> agent: <agent> confidence: <confidence> updated: <date> -->

<body — 1-3 sentences describing the memory>

> <agent> · <date> — <source>
```

**Rules:**
- Title line 1: `# 「MEM」<semantic summary>` — the `「MEM」` prefix distinguishes AI memories from user notes
- Tag line 2: `#ai/memory/<type>/entry` per the tag hierarchy
- Line 4: HTML comment with metadata fields (Bear preview ignores it, scripts parse it)
- Body: natural language, 1-3 sentences. Keep it concise and factual.
- Last line: `> agent · date — source` traceability line

**Metadata fields:**

| Field | Required | Values |
|-------|----------|--------|
| `type` | yes | `user` / `feedback` / `project` / `reference` |
| `agent` | yes | `claude-code` / `codebuddy` / `workbuddy` / `gemini` / `copilot` / `codex` |
| `confidence` | yes | `confirmed` (user explicitly stated) / `inferred` (agent deduced) |
| `updated` | yes | `YYYY-MM-DD` |

### Index Note (one per type)

```markdown
# 「MEM」<Type> Memory Index
#ai/memory/<type>

<!-- type: <type> agent: all updated: <date> -->

## 条目

- [[「MEM」title 1]] — one-line summary
- [[「MEM」title 2]] — one-line summary
```

Wiki link list. Append a new line when creating a memory. Remove the line when deleting.

## Tag Hierarchy

All memory notes live under `#ai`:

| Tag | Role |
|-----|------|
| `#ai/memory/user` | User preferences, habits, knowledge |
| `#ai/memory/user/entry` | Individual user memories |
| `#ai/memory/feedback` | Corrections, behavioral guidance |
| `#ai/memory/feedback/entry` | Individual feedback memories |
| `#ai/memory/project` | Project context, decisions, constraints |
| `#ai/memory/project/entry` | Individual project memories |
| `#ai/memory/reference` | External resource pointers |
| `#ai/memory/reference/entry` | Individual reference memories |

## Classification

Use this decision tree to determine `type`:

```
Is it about WHO the user is, what they PREFER, or how they WORK?
  → user

Is it about something the user CORRECTED or TOLD you to do differently?
  → feedback

Is it about what's HAPPENING in the project, DEADLINES, or CONSTRAINTS?
  → project

Is it about WHERE to FIND information (URLs, external systems, contacts)?
  → reference

Still uncertain → default to project
```

After creating a memory, tell the user the classification reason. If they disagree, they can retag the note directly in Bear.

## Operations

### Create Memory

```
1. Classify the memory → determine type
2. Build content following the Entry Note format
   - Include tag on line 2 (#ai/memory/<type>/entry)
   - Include tag in content (Bear MCP requires both)
3. create_note(title, content, tags: ["ai/memory/<type>/entry"])
   → returns note_id, hash
4. Find or create the index note for this type:
   search_notes(query: "「MEM」<Type> Memory Index", tag: #ai/memory/<type>)
   a. If found: edit_note to append wiki link line
   b. If not: create_note for the index note
5. embed.py --update <note_id>  (rebuild entry embedding)
6. Tell user: "Created <type> memory: <title>"
```

### Search Memory

**Structured lookup (fast, 80% of cases):**
```
search_notes(query: "keyword", tag: #ai/memory) → get matching entries
→ get_note(id) for details
```

**Semantic search (for fuzzy queries, 20% of cases):**
```
python3 memory/search.py "<query>" --top 5 --type <type>
→ returns ranked note_ids with scores
→ get_note(id) for top hits
```

**Recall what's known about the user:**
```
search_notes(query: "「MEM」", tag: #ai/memory/user/entry) → all user memories
search_notes(query: "「MEM」", tag: #ai/memory/feedback/entry) → all feedback
```

### Update Memory

```
1. get_note(id, includeContent:true) → content + hash
2. Build updated content preserving the format
3. edit_note or overwrite_note per Tag Operation Protocol (bear-notes skill)
4. embed.py --update <id>
```

### Forget Memory

```
1. get_note(id) → verify this is a memory to delete
2. trash_note(id) or archive_note(id)
3. Find the type's index note → edit_note to remove the wiki link line
4. embed.py --remove <id>
```

## Script Integration

**embed.py** — maintains `~/.bear-memory-index/embeddings.jsonl`:
```
embed.py --rebuild              Full rebuild from Bear notes
embed.py --update <note_id>     Update single entry
embed.py --remove <note_id>     Remove from index
embed.py --stats                Show index info
```

**search.py** — semantic search with hybrid ranking:
```
search.py "<query>"                    Top 5, all types
search.py "<query>" --top 10           Top 10
search.py "<query>" --type user        Filter by type
search.py "<query>" --agent claude-code  Filter by source agent
search.py "<query>" --raw              Show score breakdown
```

Ranking formula: `score = 0.6 × similarity + 0.3 × recency + 0.1 × confidence_boost`

Scripts call `bearcli` CLI internally to read note content. They do NOT modify Bear notes — all writes go through MCP tools.

## Index Maintenance

- `~/.bear-memory-index/` is per-device, not synced
- Run `embed.py --rebuild` on first use or after restoring from backup
- Run `embed.py --update <id>` after every memory create/update
- Index entries reference notes by `id` + `contentHash` — if a note is edited outside the memory workflow, the index hash won't match and the entry should be rebuilt

## Cross-Skill Dependency

This skill calls operations defined in the **bear-notes** skill:
- Note creation format (title + tag on line 2 + blank line)
- `create_note` / `get_note` / `edit_note` / `overwrite_note` / `trash_note`
- Tag Operation Protocol (read header → edit with exact text)
- MCP Availability Check (verify tools loaded before operating)

If bear-notes skill is not loaded, all Bear operations must be prefixed with `mcp__bear__`.
