---
name: bear-notes
description: Use when working with Bear notes — creating, editing, organizing, writing, or managing notes. Triggers on: Bear notes, 笔记, 写笔记, 创建笔记, 整理笔记, 标签, note format, Markdown notes. Also triggers on any Bear issue: 笔记冲突, 笔记置顶, Bear 冲突, 笔记异常, conflict badge. Covers both MCP operations and note writing conventions. ⛔ NEVER use add_tags/remove_tags/rename_tag/delete_tag — they modify note body. Always use edit_note for tag changes per Tag Operation Protocol.
---

# Bear Notes

Covers two aspects: note writing conventions and MCP operations (using Bear's built-in MCP server).

⛔ **TAG SAFETY: NEVER use add_tags / remove_tags / rename_tag / delete_tag.**
They modify the note body and break the tag-on-line-2 convention.
Always use `edit_note` for tag changes. See [Tag Operation Protocol](#tag-operation-protocol).

## Note Writing Conventions

### Structure Template

Every note follows this format:

```
行1: # 标题
行2: #标签
行3: 空行
行4: 正文（可选头图或引言）
```

Tags always go on line 2, immediately after the title. Never place tags at the end of the note body.

### Tag Assignment

When creating a note, analyze its content and assign it to the most specific existing tag in the hierarchy. Do NOT default to a generic tag — always match to the best-fitting leaf tag.

**Process**: read the note content → identify its domain (work, tech, life, family, etc.) → match to the deepest applicable tag → use that tag on line 2.

**Example**: a note about home renovation does NOT go under `#log` — it goes under `#log/home`. A note about a work feature does NOT go under `#tme` — it goes under `#tme/feature/YYYY/MM`.

Only create a new tag when no existing tag fits the content. For the full tag hierarchy, load `reference/tag-system.md`.

### Headings

Use `##` for top-level sections and `###` for subsections. Don't use `#` inside the note body (that's reserved for the title). Don't skip levels — always `##` → `###`.

```
## 一级章节
### 二级小节
```

### Wiki Links

Use `[[Note Title]]` to link between related notes. This is one of Bear's most powerful features for building a knowledge network. Type `[[` and a few letters of the target note title — Bear auto-completes it.

```
See also: [[RAC | Dive to the Deep]], [[关于 MVC 的一个常见误用]]
```

Use a pipe `|` to customize the display text: `[[Actual Note Title|display text]]`.

### Text Formatting

| Style | Markdown | Use for |
|-------|----------|---------|
| Bold | `**text**` | Key terms, emphasis |
| Italic | `*text*` | Subtle emphasis |
| Highlight | `==text==` | New/important concepts |
| Strikethrough | `~~text~~` | Deprecated/outdated info |
| Inline code | `` `text` `` | Shortcuts, commands, code symbols |
| Code block | ` ```lang ` | Multi-line code snippets |
| Blockquote | `> text` | External references, quotes |
| Horizontal rule | `---` | Major section breaks |

### Lists

```markdown
* Bullet list item
* Another item
  * Nested item (indent with 2 spaces)

1. Numbered list
2. Second item

- [ ] Todo item
- [x] Completed item
```

### Blockquote for References

When citing external sources, use blockquotes:

```markdown
> 此文是对 @onevcat 的 [关于 MVC 的一个常见的误用](https://onevcat.com/2018/05/mvc-wrong-use/) 一文的笔记。
```

### Date-Prefixed Titles (user's convention)

The user uses a `YYYYMMDD | Title` format for diary, feature, and meeting notes. This provides natural chronological ordering.

```markdown
diary:    20250224 | 活在过去的人
feature:  20260520 | AI 唱在minibar入口的展示规则优化
meeting:  20260520 | 日报
```

### Images

Bear supports drag-and-drop images. Official notes use a hero/banner image after the tag line. Use images sparingly to illustrate key points.

### Horizontal Rules for Long Notes

Use `---` to separate major sections in longer notes. This improves readability for notes with distinct topic blocks.

### Footnotes

Use `[^1]` for supplementary information. Define the footnote at the bottom of the note:

```markdown
Some text with a footnote[^1].

[^1]: The footnote content at the bottom.
```

---

## MCP Availability Check

**Before any Bear operation**, verify the MCP tools are loaded:

1. Check your available tool list for `search_notes`, `create_note`, `get_note`.
2. **If these tools are NOT present:**
   - Stop. Do not attempt any Bear operations.
   - Tell the user: "Bear MCP is not configured for this agent. See `reference/mcp-tools.md` for setup instructions."
3. **If tools ARE present**, proceed with the operation below.

## Tag Operation Protocol

The core principle: **read the header first, then edit with exact text.** Never use `add_tags` / `remove_tags` / `rename_tag` / `delete_tag` — they all modify the note body. Pure `edit_note` with exact text matching is the only clean path.

Every tag operation starts with:
```
read_note_content(id) → inspect first ~200 bytes
```
This gives the exact text of line 1 (title), line 2 (tag or empty), line 3 (blank), and line 4+ (body start). Use these exact strings in the edits below — never guess or reconstruct them.

**Case A: Migrate tag** (`#oldtag` → `#newtag`)

```
From header:
  title_line = line 1  (e.g., "# 20250224 | 活在过去的人")
  tag_line   = line 2  (e.g., "#diary/2022/10")

edit_note(id, edits: [{
  find:    "{title_line}\n{tag_line}",
  replace: "{title_line}\n#newtag"
}])
```

**Case B: Add tag to untagged note** (empty line 2 → `#newtag`)

```
From header:
  title_line      = line 1
  body_after_l2   = first ~20 chars immediately after the blank line 2
                     (may be body text directly, or another blank line + body)

edit_note(id, edits: [{
  find:    "{title_line}\n\n{body_after_l2}",
  replace: "{title_line}\n#newtag\n\n{body_after_l2}"
}])
```
Note: The replace string inserts `#newtag\n` and ensures exactly one blank line separates the tag from body.

**Case C: Remove tag** (`#oldtag` → untagged, rare)

```
From header:
  title_line      = line 1
  tag_line        = line 2
  first_body_line = first ~20 chars of line 4

edit_note(id, edits: [{
  find:    "{title_line}\n{tag_line}\n\n{first_body_line}",
  replace: "{title_line}\n\n{first_body_line}"
}])
```

**Post-operation verification (all cases):**
```
get_note(id, includeContent:false)
→ Check tags field: exactly one tag (expected), no unexpected extras
→ Check contentHash changed (confirms edit applied)
→ Optional: read_note_content(id) spot-check first 4 lines
```

## Safety Rules

**1. `overwrite_note` requires `baseHash`.** Always `get_note` first to obtain the content hash. The write is rejected if the note changed in between.

**2. `edit_note` edits are atomic.** All `find` strings must match, or no changes are committed. Prefer `edit_note` for targeted changes.

**3. Tag changes follow the [Tag Operation Protocol](#tag-operation-protocol).** Never use `add_tags` / `remove_tags` / `rename_tag` / `delete_tag` — they all modify the note body.

**4. Write → verify.** After every write, call `get_note(id)` and inspect the returned metadata — MCP writes return changed fields, so unintended side effects are detectable.

**5. `search_notes` uses Bear's native search syntax.** `@today`, `@tagged`, `@untagged`, `#tag`, `"exact phrase"`, `-negation`. See [Bear's search documentation](https://bear.app/faq/how-to-search-notes-in-bear/).

## General Operation Patterns

**Create a note:**
```
1. Include the tag on line 2 of content (tags param places tags at bottom per Bear setting)
2. create_note(title, content: "# Title\n#tag\n\nBody...", tags: ["tag"]) → returns id, hash
3. MUST run [Format Validation](#note-format-validation) — NOT optional.
   create_note often inserts a blank line before the tag (tag ends up on line 3).
   Catch and fix this immediately.
```

**Generic body edit:**
```
1. get_note(id, includeContent:true) → content + hash
2. edit_note(id, edits: [{find: "old", replace: "new"}]) → returns changed fields
3. get_note(id) verify
```

**Full rewrite:**
```
1. get_note(id, includeContent:true) → content + hash
2. Construct new content preserving tag on line 2
3. overwrite_note(id, content, baseHash: hash) → returns changed fields
```

**Search then read:**
```
1. search_notes(query: "...", includeContent:false) → metadata array
2. For each hit: get_note(id, includeContent:true)
```

**Batch verification:**
| Check | Method |
|-------|--------|
| Untagged notes | `search_notes(query: "@untagged")` → array length |
| Tag on line 2 | `read_note_content(id)` → check first 4 lines |
| Duplicates today | `search_notes(query: "@today")` → inspect titles |
| Tag counts | `search_notes(query: "#tag")` → array length |

## Note Format Validation

**Every create_note MUST be followed by this check immediately — no exceptions.**

```
1. create_note(...) → returns id
2. read_note_content(id) → check first 3 lines:

   Line 1: # Title          ← must be the title, not blank
   Line 2: #tag             ← must be the tag line, NOT blank
   Line 3:                  ← must be blank

3. If line 2 is blank (tag appears on line 3 → "double-blank bug"):
   edit_note immediately:
     find:    "# {title}\n\n#tag"
     replace: "# {title}\n#tag"
   
4. Confirm: get_note(id, includeContent:false) → tags field correct
```

This check takes < 1 second per note and prevents the most common formatting bug
in the entire workflow. Do NOT skip it — even (especially) when creating many notes
in parallel.

---

## 参考文件

以下内容按需通过 Read 加载，不做会话启动注入：

| 文件 | 内容 | 触发条件 |
|------|------|---------|
| `reference/mcp-tools.md` | MCP 配置、25 工具速查表、已知问题 | 配置 MCP / 排查异常 |
| `reference/tag-system.md` | 标签体系统计、官方 vs 用户对照、TagCon | 了解标签全貌 |
| `reference/feature-template.md` | Feature 笔记状态追踪模板 | 创建 feature 笔记 |
