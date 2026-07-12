---
name: bear-memory
description: Persistent memory for AI agents. MUST be loaded at the start of EVERY conversation to recall user preferences, feedback, and project context. Also triggers on: remember, 记忆, recall, 回忆, forget, 忘记, memory, what do you know about me, 你知道我, 之前说过, 之前, 上次, preferences, 偏好, 规则, rules, 规范, conventions, 约定, 流程, workflow, 怎么做的, how to, 项目知识, 开发方式, 工作习惯, 习惯. Agent MUST proactively write new memories when learning user preferences, receiving corrections, or capturing project decisions — do NOT wait for the user to say "remember this." Depends on bear-notes skill for Bear MCP operations.
---

# Bear Memory

Persistent memory system for AI agents backed by Bear notes. Two-layer storage (index + entry topic notes) with semantic search via local embeddings. Follows the CoALA framework (user / feedback / project / reference).

**Prerequisites:**
- bear-notes skill loaded (MCP operations + Tag Protocol)
- `skills/memory/requirements.txt` installed (`pip3 install -r requirements.txt`)
- `embed.py --rebuild` run at least once

## Memory Note Format

### Entry Note — Topic Grouped (one topic per note, multiple `##` sections)

Each note is a **topic container** with one or more `##` sections, each section being one memory item.

```markdown
# 「MEM」<Type> · <Topic>
#ai/memory/<type>/entry

<!-- updated: <date> -->

## <section title>
<!-- type: <type> agent: <agent> confidence: <confidence> updated: <date> -->

<body — 1-3 sentences describing the memory>

> <agent> · <date> — <source>

## <section title>
<!-- type: <type> agent: <agent> confidence: <confidence> updated: <date> -->

<body>

> <agent> · <date> — <source>
```

**Rules:**
- Title line 1: `# 「MEM」<Type> · <Topic>` — Type 首字母大写（User / Feedback / Project / Reference），`·` 分隔，Topic 是 broad topic 非单条记忆标题。示例：`「MEM」User · 编码偏好`
- Tag line 2: `#ai/memory/<type>/entry` per the tag hierarchy
- Line 4: `<!-- updated: <date> -->` — note-level, only the `updated` field. Not a full metadata comment.
- Sections ordered **newest first** — append with `position="beginning"`, latest memory at top
- Each `##` section = one memory item:
  - Section header: `## <section title>` — concise title for this memory
  - Next line: `<!-- full metadata -->` — `type`, `agent`, `confidence`, `updated`
  - Body: natural language, 1-3 sentences. Keep it concise and factual.
  - Last line of section: `> agent · date — source` traceability
- All sections within a note share the same `type`

**Metadata fields (per section):**

| Field | Required | Values |
|-------|----------|--------|
| `type` | yes | `user` / `feedback` / `project` / `reference` |
| `agent` | yes | `claude-code` / `codebuddy` / `workbuddy` / `gemini` / `copilot` / `codex` |
| `confidence` | yes | `confirmed` (user explicitly stated) / `inferred` (agent deduced) |
| `updated` | yes | `YYYY-MM-DD` |

**Why topic grouping:** Reduces note count (6 memories → ~2 notes), related memories naturally aggregate, easier to browse vs. dozens of single-entry notes.

### Index Note (one per type)

```markdown
# 「MEM」<Type> Memory Index
#ai/memory/<type>

<!-- type: <type> agent: all updated: <date> -->

## 条目

- [[「MEM」<Type> · <Topic>]] — topic summary
- [[「MEM」<Type> · <Topic>]] — topic summary
```

Wiki link list. Append a new line when creating a new topic note. Remove the line when deleting the note.

## Tag Hierarchy

All memory notes live under `#ai`:

| Tag | Role |
|-----|------|
| `#ai/memory/user` | User preferences, habits, knowledge |
| `#ai/memory/user/entry` | User memory topic notes |
| `#ai/memory/feedback` | Corrections, behavioral guidance |
| `#ai/memory/feedback/entry` | Feedback memory topic notes |
| `#ai/memory/project` | Project context, decisions, constraints |
| `#ai/memory/project/entry` | Project memory topic notes |
| `#ai/memory/reference` | External resource pointers |
| `#ai/memory/reference/entry` | Reference memory topic notes |

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

## Proactive Memory Protocol

This skill is NOT only reactive. The agent must proactively recall and write memories without waiting for explicit user commands.

### When to Auto-Recall Memories

**At the start of EVERY conversation:**
```
search_notes(query: "「MEM」", tag: #ai/memory/user/entry) → load user preferences
search_notes(query: "「MEM」", tag: #ai/memory/feedback/entry) → load behavioral feedback
```
Keep these in context throughout the conversation. They are your persistent knowledge about the user.

**When the user asks about project conventions, rules, workflows, or personal preferences:**
Use `search_notes` tool to search `#ai/memory` BEFORE composing your answer. Do NOT rely on preloaded memories alone — they may have expired.

**Before starting a task that involves a known project:**
```
search_notes(query: "「MEM」", tag: #ai/memory/project/entry) → load project constraints
```

**When unsure about how to behave:**
```
python3 skills/memory/search.py "<query about the situation>" --type feedback
→ Check if user has previously corrected similar behavior
```

**Silent recall — do NOT announce.** Just read the memories and apply them. The user doesn't need to hear "I found 3 memories about you." Only mention memories if they directly inform a decision you made.

### When to Auto-Write Memories

**The user states a preference, habit, or personal fact:**
→ Create a `user` memory immediately. Example: "I always use tabs" → write it down.

**The user corrects your behavior or tells you to do something differently:**
→ Create a `feedback` memory immediately. This is critical — corrections must be remembered or you'll make the same mistake again.

**A project decision, deadline, or constraint is discussed:**
→ Create a `project` memory. Example: "We decided to use PostgreSQL instead of MySQL."

**An external resource (URL, doc, contact) is referenced that will be useful later:**
→ Create a `reference` memory.

**Write to Bear** — NEVER use built-in agent memory or /memory command. Target: `#ai/memory/<type>/entry` notes. Don't interrupt the conversation with "I'll remember that." Just create the memory. If the user should know, a brief one-line confirmation at the end of your response is sufficient.

### When NOT to Write

- Trivial facts that won't matter in future conversations (e.g., "the test passed")
- Information already captured in an existing memory (check before writing)
- Temporary state (e.g., "currently in the middle of refactoring X")

→ For HOW to create memories: see **Create Memory** protocol below.

## Operations

### Create Memory

Note: Tag changes in Bear must follow the **Tag Operation Protocol** in bear-notes skill. NEVER use add_tags/remove_tags.

```
1. Classify the memory → determine type
2. Build the memory body (1-3 sentences) + source line
3. **REQUIRED — do NOT skip.** Run semantic grouping before any write:
   ```
   python3 skills/memory/search.py --find-group "<body text>" --type <type>
   ```
   → returns `{"note_id": "...", "similarity": N}` or `{}`

   ⚠️ Manual keyword search (`search_notes`) is NOT a substitute for this step.
   Two memories may use different keywords but have identical semantics
   (e.g., "方案中文输出" and "优先使用中文" both describe 中文 language preference).
   An empty keyword search does NOT mean no matching topic note exists.

   → If match found (similarity ≥ 0.48):
      - get_note(id=note_id, includeContent=true) → get content + title
      - Build the new section content:
        \n\n## <section title>\n<!-- type: <type> agent: <agent> confidence: <confidence> updated: <date> -->\n\n<body>\n\n> source
      - append_to_note(id=note_id, content=<new section>, position="beginning")
      - embed.py --update <note_id>
      - Tell user: "Appended to <type> memory topic: <topic title>"

   b. If no match:
      - Build content as new topic note:
        Line 1: # 「MEM」<Type> · <Topic>
        Line 2: #ai/memory/<type>/entry
        (blank)
        <!-- updated: <date> -->
        (blank)
        ## <section title>
        <!-- type: <type> agent: <agent> confidence: <confidence> updated: <date> -->
        (blank)
        <body>
        (blank)
        > source
      - create_note(title, content, tags: ["ai/memory/<type>/entry"])
        → returns note_id, hash
      - **RUN bear-notes Format Validation immediately** (check tag is on line 2, fix if blank-line bug)
      - **Memory-specific check:** verify `<!-- updated: <date> -->` on line 4,
        each `##` section has a valid metadata comment on the next line
      - embed.py --update <note_id>

4. Find or create the index note for this type:
   search_notes(query: "「MEM」<Type> Memory Index", tag: #ai/memory/<type>)
   a. If found: edit_note to append wiki link line (only on new topic note creation)
   b. If not: create_note for the index note
5. embed.py --update <note_id>  (re-index — removes old entries, adds all sections)
6. Tell user: "Created <type> memory topic: <title>" or "Appended to <title>"
```

**Grouping threshold:** 0.48 (cosine similarity against topic note centroid, calibrated for `paraphrase-multilingual-MiniLM-L12-v2`). Override with `--threshold <value>`.

### Search Memory

**Structured lookup (fast, 80% of cases):**
```
search_notes(query: "keyword", tag: #ai/memory) → get matching entries
→ get_note(id) for details
```

**Semantic search (for fuzzy queries, 20% of cases):**
```
python3 skills/memory/search.py "<query>" --top 5 --type <type>
→ returns ranked note_ids + section_index + section_title with scores
→ get_note(id) for full note (all sections)
```

**Find group for new memory:**
```
python3 skills/memory/search.py --find-group "<body>" --type <type>
→ returns {"note_id": "...", "similarity": N} or {}
Use --threshold 0.45 to temporarily lower the threshold for edge cases
```

**Recall what's known about the user:**
```
search_notes(query: "「MEM」", tag: #ai/memory/user/entry) → all user topic notes
search_notes(query: "「MEM」", tag: #ai/memory/feedback/entry) → all feedback topic notes
```

## Cross-Skill Dependency

This skill calls operations defined in the **bear-notes** skill:
- Note creation format (title + tag on line 2 + blank line)
- `create_note` / `get_note` / `edit_note` / `overwrite_note` / `trash_note` / `archive_note` / `append_to_note`
- Tag Operation Protocol (read header → edit with exact text)
- MCP Availability Check (verify tools loaded before operating)

If bear-notes skill is not loaded, all Bear operations must be prefixed with `bear__`.

---

## 参考文件

以下内容按需通过 Read 加载：

| 文件 | 内容 | 触发条件 |
|------|------|---------|
| `docs/memory-operations.md` | Update / Forget 记忆完整流程 | 更新或删除记忆 |
| `docs/migration.md` | 旧格式迁移三阶段 | 用户触发迁移 |
| `docs/scripts.md` | embed.py / search.py 参数、索引维护 | 运行脚本 / 重建索引 |
