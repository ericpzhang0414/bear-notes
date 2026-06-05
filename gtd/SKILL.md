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
- [ ] `[L]` `📌 日常` description
    > context / detail
    > 📅 YYYY-MM-DD
    > 📍 location
    > from @source
- [ ] 🌟 `[L]` `📌 日常` urgent description
```

- **Checkbox:** `- [ ]` active, `- [x]` done (then archive)
- **Priority (optional):** `🌟` after checkbox, before domain. Marks urgent/important items — they sort first within their domain. Only use when truly needed.
- **Domain (required):** `` `[L]` `` Life or `` `[W]` `` Work, in backticks for monospace alignment
- **Type (required):** `` `emoji 中文` `` in backticks (see table). Unified by activity type.
- **Item descriptor:** clear action description after the markers — no project prefix needed
- **Blockquote order:** content → 📅 time → 📍 location → from source
- **Sort order within each section:**
  1. `[L]` items before `[W]` items
  2. Within same domain: 🌟 items before non-🌟 items
  3. Within same domain × 🌟 group:
     a. Items with `📅 YYYY-MM-DD` date → ascending by date (soonest first; overdue even sooner)
     b. Items without date → after all dated items, newest-added first
  → Date source: `📅 YYYY-MM-DD` in description line or blockquote `> 📅 YYYY-MM-DD`

### 🌟 Detection (during batch organize)

Scope: item description line (after markers, excluding blockquote `> ` lines).

| Source | Rule |
|--------|------|
| User manually placed `🌟` anywhere in item | Normalize to standard position (after checkbox, before domain). If already in standard position, skip. |
| Keywords: 紧急, 重要, 高优先, ASAP, urgent | Auto-mark 🌟 — show in summary as "auto-detected" for user review. Case-insensitive for English keywords. |
| Dedup | If 🌟 already applied (manual or auto), skip further auto-marking for this item. |
| Negation guard | If keyword is negated (不紧急, 不重要, not urgent), do NOT auto-mark. |

## Domain & Type Markers

### Domain
| `` `[L]` `` | Life  | `` `[W]` `` | Work  |

### Type (unified by activity, not domain)
| Marker | Activity | Examples |
|--------|----------|---------|
| 💻 `开发` | Develop / implement | Feature, code |
| 👀 `评审` | Review / inspect | Code review, visual QA |
| 🤖 `智能` | AI / tools | AI-Coding, automation |
| 🔎 `调研` | Research / evaluate | Tech spike, solution evaluation |
| 🐛 `修复` | Fix issues | Bugs, crashes, online issues |
| 🧪 `测试` | Test / QA | Unit test, integration test, QA |
| 📌 `日常` | Errand / admin | Documents, shopping, appointments, medical |
| ✈️ `出行` | Travel | Flights, hotels, itinerary |
| 🔧 `维修` | Repair / maintain | Car, home, appliances |

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
replace: "## 📥 Index Box\n\n- [ ] `[W]` `开发` new task\n\n## 📋 Next Actions"
```

**Into a populated section** — find the correct insertion point respecting all sort rules:

1. **Identify target group** (L🌟 / L / W🌟 / W) based on domain and 🌟 status
2. **Within that group, find date-based position:**
   - If new item has `📅 YYYY-MM-DD`: insert so dates stay ascending (soonest first). Scan existing dated items in group, find where new date fits chronologically.
   - If new item has no date: insert after the last dated item in group, before the first undated item (undated items sorted newest first).
3. **Edge cases:** If target group is empty, insert at group boundary. Use adjacent item or section boundary as anchor.

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
  {find: "- [ ] `[W]` `开发` task name\n\n## 📋 Next Actions",
   replace: "## 📋 Next Actions"},
  {find: "last item in Next Actions\n\n## 💡 Someday",
   replace: "last item in Next Actions\n- [ ] `[W]` `开发` task name\n\n## 💡 Someday"}
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
replace: "- [x] last completed item\n- [x] `[W]` `开发` done task\n    > 📅 2026-06-05\n\n### WORK"
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
4. 🌟 Detection (per item, description line only, skip if negated: 不紧急/不重要/not urgent):
   a. Scan for existing 🌟 (any position) → normalize to standard position. If already standard, skip.
   b. If no 🌟 from step a, scan keywords (紧急/重要/高优先/ASAP/urgent, case-insensitive) → auto-mark 🌟
   c. Flag auto-detected 🌟 in summary for user review
5. Show proposed format (with 🌟 annotations) → user confirms
6. edit_note to replace with standard GTD format
```

Format to apply:
```
- [ ] `[L]` `📌 日常` 去物业中心拿租房合同
- [ ] 🌟 `[L]` `📌 日常` 紧急事项
```

**Step 2: Classify Index Box items**

Auto-classify first, then ask user for remaining items:

```
For each item in Index Box:
  ├─ Has future date (📅 YYYY-MM-DD) within ≤ 7 days of today → auto → Next Actions
  ├─ Contains keywords (今天/明天/这周/尽快/紧急/ASAP) → auto → Next Actions
  └─ Otherwise → ask user: Next Actions? / Someday / Maybe? / Delete?
```

Show summary with auto-classified items labeled, user confirms all at once.
- **Next Actions** / **Someday / Maybe** — move per Move protocol (respecting 🌟 sort order)
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
