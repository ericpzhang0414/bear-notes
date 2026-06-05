---
name: bear-gtd
description: Manage the GTD (Getting Things Done) TODO list in Bear. Triggers on any task-related action — capture (记一下/备忘/记录/加条/capture), view (看看/有什么任务/今天做什么/清单/list), complete (完成/搞定/done/做完了), move (移到/移动/搬到/提升/move), edit (修改/更新/改一下/edit), delete (删掉/放弃/不做了/remove), review (回顾/梳理/整理/清理/review), archive (归档/存档/archive), batch organize (整理gtd/整理todo/整理待办/清理gtd/清理todo/清理待办/cleanup gtd). Also triggers on section names: Next Actions, Someday, Maybe, Index Box, inbox. When in doubt, use this skill if the user is talking about a task they want to track or manage.
---

# Bear GTD — TODO List Manager

**This skill operates ONLY on the existing note `📥 GET THINGS DONE NOW` (`#log/todo`).**
Never create new GTD notes. All task operations — add, move, complete, archive — target this single note.

## Note Structure

```
## 📥 Index Box        ← Quick capture, process during weekly review
## 📋 Next Actions     ← Committed: doing now or next
## 💡 Someday / Maybe  ← Want to do, not committed (review weekly)
## 📦 Archive          ← Links to yearly archives, newest first
```

**Pipeline:** Index Box → (process) → Next Actions / Someday / Maybe / delete
**Archive:** Completed items go to `GTD ARCHIVE YYYY` notes. Links sorted newest first:

```
## 📦 Archive
→ [[GTD ARCHIVE 2026]]
→ [[GTD ARCHIVE 2025]]
→ [[GTD ARCHIVE 2024]]
```

Create a new `GTD ARCHIVE YYYY` at the start of each year.

## Item Format

```
- [ ] `[L]` `📌 task` description
    > context / detail
    > 📅 YYYY-MM-DD
    > 📍 location
    > from @source
```

- **Checkbox:** `- [ ]` active, `- [x]` done (then archive)
- **Domain (required):** `` `[L]` `` Life or `` `[W]` `` Work, in backticks for monospace alignment
- **Type (required):** `` `emoji type` `` in backticks (see table). Unified by activity type.
- **Item descriptor:** clear action description after the markers — no project prefix needed
- **Blockquote order:** content → 📅 time → 📍 location → from source
- **Sort order:** all `[L]` items before all `[W]` items within each section

## Domain & Type Markers

### Domain
| `` `[L]` `` | Life  | `` `[W]` `` | Work  |

### Type (unified by activity, not domain)
| Marker | Activity | Examples |
|--------|----------|---------|
| 💻 `dev` | Develop / implement | Feature, code |
| 👀 `review` | Review / inspect | Code review, visual QA |
| 🤖 `ai` | AI / tools | AI-Coding, automation |
| 🔎 `research` | Research / evaluate | Tech spike, solution evaluation |
| 🐛 `bug` | Fix issues | Bugs, crashes, online issues |
| 🧪 `test` | Test / QA | Unit test, integration test, QA |
| 📌 `task` | Errand / admin | Documents, shopping, appointments, medical |
| ✈️ `trip` | Travel | Flights, hotels, itinerary |
| 🔧 `fix` | Repair / maintain | Car, home, appliances |

## Operations

All operations target the `📥 GET THINGS DONE NOW` note. Always call `get_note(id)` before any write — the note may have changed.

### Find the TODO note
```
search_notes(query: "📥 GET THINGS DONE NOW") → id "D5807CB4..."
```
The note is pinned globally, always findable by title.

### View tasks
Read the full note: `read_note_content(id)`. Optionally filter by section, domain (`[L]`/`[W]`), or type.

### Add a task
Determine domain, type, and section from the user. Default to Index Box if unclear.

**Into an empty section** — anchor on the section boundary:
```
find:    "## 📥 Index Box\n\n## 📋 Next Actions"
replace: "## 📥 Index Box\n\n- [ ] `[W]` `dev` new task\n\n## 📋 Next Actions"
```

**Into a populated section** — find the correct insertion point maintaining L before W within the section:
- Scan existing items, identify the last `[L]` item and last `[W]` item
- Insert new `[L]` item before the first `[W]` item (or before next section if no `[W]`)
- Insert new `[W]` item after the last `[W]` item (or after last `[L]` if no `[W]`)
- Use the boundary between the last item and next section as the anchor

### Update a task
Use exact text match of the current item line. Ask the user what to change (description, type, domain, or notes).

```
find:    "exact current item line"
replace: "updated item line"
```

Include blockquote lines in the find if they exist — they're part of the task.

### Move between sections
Use two atomic edits in a single `edit_note` call:
1. **Cut** — remove item from source section (anchor: item + surrounding boundaries)
2. **Paste** — insert into target section (maintaining L-before-W order)

Example: Move item from Index Box to Next Actions:
```
edits: [
  {find: "- [ ] `[W]` `dev` task name\n\n## 📋 Next Actions",
   replace: "## 📋 Next Actions"},
  {find: "last item in Next Actions\n\n## 💡 Someday",
   replace: "last item in Next Actions\n- [ ] `[W]` `dev` task name\n\n## 💡 Someday"}
]
```

Common moves:
- Index Box → Next Actions (now committed)
- Index Box → Someday / Maybe (not now)
- Someday / Maybe → Next Actions (promoted)
- Delete: remove from any section without re-inserting (drop the task)

### Archive a completed task
Multi-step operation across two notes. Not atomic — verify each step.

1. `edit_note` on TODO: change `- [ ]` to `- [x]`
2. `read_note_content` the target `GTD ARCHIVE YYYY` (current year)
3. `edit_note` on archive: insert the completed item. Anchor on existing items in the archive.
4. `edit_note` on TODO: remove the completed item (same pattern as Delete/Move cut)

**Archive anchor example:**
```
find:    "- [x] last completed item\n\n### WORK"
replace: "- [x] last completed item\n- [x] `[W]` `dev` done task\n    > 📅 2026-06-05\n\n### WORK"
```

### Weekly review
When user says "review" or "周回顾":
1. Read the TODO note
2. For each item in Index Box, ask: "→ Next Actions, Someday/Maybe, or drop?"
3. Process items one at a time using Move patterns above
4. Also review Someday/Maybe — ask if any should promote to Next Actions

### Batch Organize（整理 gtd / 整理待办）

Trigger: 整理 gtd, 整理 todo, 整理待办, 清理 gtd, 清理 todo, 清理待办, cleanup gtd

Executes 5 steps in order. Bulk operations do NOT need per-item confirmation — show summary, user confirms once.

**Step 1: Normalize Index Box items**

```
1. Read Index Box section
2. Find bare-text entries (no domain/type markers)
3. Infer domain ([L]/[W]) and type from keywords
4. Show proposed format → user confirms
5. edit_note to replace with standard GTD format
```

Format to apply:
```
- [ ] `[L]` `task` 去物业中心拿租房合同
```

**Step 2: Classify Index Box items**

For each item in Index Box, ask user:
→ Next Actions? / Someday / Maybe? / Delete?

- **Next Actions** — move per Move protocol
- **Someday / Maybe** — move per Move protocol
- **Delete** — remove from note entirely (not worth doing, don't keep)

**Step 3: Delete strikethrough items**

```
1. Search TODO note for ~~text~~ patterns
2. Delete all matching items — remove from note entirely
3. No confirmation needed — strikethrough = explicit delete signal
```

**Step 4: Move completed to Done**

```
1. Search TODO note for all - [x] items
2. Show summary → user confirms
3. For each - [x] item:
   - Remove from source section
   - Insert at TOP of ## ☑️ Done (newest first)
```

Done section sort order: newest completed at top (reverse chronological).

**Step 5: Auto-archive Done when full**

```
1. After Step 4, count items in ## ☑️ Done
2. If ≥ 20:
   - Notify user: "Done has N items, archiving all to GTD ARCHIVE YYYY"
   - Move all Done items to current year's GTD ARCHIVE YYYY note
   - Clear Done section
3. No extra confirmation — threshold triggers auto-archive
```

**Pipeline summary:**

```
条目去向:
  ├─ 正常完成 (- [x]) → ☑️ Done (最前) → [≥20条触发] → 📦 Archive
  └─ 废弃 (~~text~~)  → Delete (彻底移除，无确认)
```

## Format Validation
After any write, verify:
- Tag `#log/todo` on line 2, no blank before it (fix with edit_note if needed)
- `[L]` items before `[W]` items within each section
- Every item has `` `[L]` `` / `` `[W]` `` and a type marker
- No `- [x]` items remain in TODO note — they must be archived
- Blank lines between sections, not between items within a section
