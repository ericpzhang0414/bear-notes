# bear-notes

AI agent skill for Bear notes — note writing conventions, MCP CRUD operations, and a proactive persistent memory system. Supports Claude Code, CodeBuddy, WorkBuddy, Gemini CLI, Copilot CLI, and Codex CLI.

## Capabilities

**Note Writing Conventions** — structure template (title + tag on line 2 + body), heading rules (`##`/`###` only), wiki links (`[[Note Title]]`), text formatting, task lists with status checklists, date-prefixed titles (`YYYYMMDD | Title`), blockquote references, footnotes, TagCon icons.

**Tag System Reference** — 7 top-level tags (`#tme`, `#tech`, `#diary`, `#archive`, `#log`, `#read`, `#family`) with a hierarchical assignment protocol that matches content to the deepest applicable leaf tag.

**MCP Operations** — 25 MCP tools via Bear's built-in `bearcli mcp-server`, covering full CRUD, search with Bear's native query syntax, tag/pin/attachment management, and note lifecycle (trash/archive/restore). Safety rules: `overwrite_note` requires `baseHash`, `edit_note` edits are atomic, write-then-verify on every operation.

**Tag Operation Protocol** — safe tag editing via `edit_note` with exact text matching. Never uses `add_tags`/`remove_tags`/`rename_tag`/`delete_tag` (they modify the note body). Three documented cases: migrate tag, add tag to untagged note, remove tag.

**Proactive Memory System** — agents automatically recall user preferences, feedback, and project context at session start. They proactively write new memories when learning preferences, receiving corrections, or capturing decisions — no need to say "remember this." Topic-grouped notes (`「MEM」Type · Topic`) with `##` sections, semantic search with hybrid ranking, and deterministic centroid-based clustering. Four CoALA memory types (user, feedback, project, reference). Cross-agent memory sharing via Bear notes under `#ai/memory`.

## Install

```bash
git clone <repo-url> bear-notes
cd bear-notes
./install.sh
```

Runs 7 phases automatically:
1. Detect installed agents (Claude Code / CodeBuddy / WorkBuddy / Gemini / Copilot / Codex)
2. Check for old versions (backup if found)
3. Install skill via symlink
4. Configure Bear MCP for each agent
5. Install memory system (Python deps + embedding index rebuild)
6. Configure proactive memory recall in agent global instructions
7. Verify installation and print report

### Options

```
./install.sh              # Auto-detect, install, configure MCP, setup memory, configure recall, verify
./install.sh --check      # Verify only, no changes
./install.sh --force      # Skip confirmation on old version replacement
./install.sh --no-memory  # Skip memory system setup (pip install + index rebuild)
./install.sh --no-recall  # Skip global instruction auto-config
./install.sh --uninstall  # Remove all symlinks (MCP config preserved)
```

### Key Commands

```bash
# Memory indexing & search
python3 memory/embed.py --rebuild          # Rebuild embedding index
python3 memory/embed.py --stats            # Show note count, section count, type distribution
python3 memory/search.py "<query>"         # Semantic search (with section info)
python3 memory/search.py --find-group "text" --type user  # Find best topic note to group with

# Migration (old 1:1 format → topic-grouped)
python3 memory/embed.py --migrate-plan     # Phase 1: review grouping plan (read-only JSON)
# → Agent executes via MCP                 # Phase 2: create topic notes, archive old ones
python3 memory/embed.py --rebuild          # Phase 3: rebuild index

# Testing
python3 test_memory.py                     # Run comprehensive test suite (37 tests)
```

## Memory System

The `memory/` subdirectory provides a proactive persistent memory layer so AI agents can remember across sessions without explicit user commands.

**Format:** Topic-grouped notes — one note per topic (`「MEM」User · 编码偏好`), each `##` section is one memory item. Sections ordered newest first (append with `position="beginning"`). Auto-grouping via max-section cosine similarity (threshold 0.48, calibrated for `paraphrase-multilingual-MiniLM-L12-v2`).

**Proactive Protocol:** Agents recall memories silently at session start and write new memories without being asked. See `memory/SKILL.md` → Proactive Memory Protocol for the full specification.

| Component | Purpose |
|-----------|---------|
| `memory/SKILL.md` | Memory sub-skill — format spec, classification, proactive protocol, CRUD operations |
| `memory/embed.py` | Embedding builder — per-section indexing, `--migrate-plan` for clustering, `--stats` |
| `memory/search.py` | Semantic search with hybrid ranking, `--find-group` for topic matching |
| `memory/requirements.txt` | Python deps: `sentence-transformers>=5.0`, `numpy>=2.0` |
| `test_memory.py` | Comprehensive test suite — 37 tests covering all components |

**Memory types:** `user` (who you are, preferences), `feedback` (corrections, behavioral guidance), `project` (deadlines, constraints, decisions), `reference` (external resource pointers).

**Model:** `paraphrase-multilingual-MiniLM-L12-v2` — optimized for multilingual (Chinese + English) semantic similarity.

**Scoring:** `0.6×similarity + 0.3×recency + 0.1×confidence`. Search uses per-section vectors. Grouping uses max section similarity (find-group) or centroid comparison (migrate-plan).

**Index:** `~/.bear-memory-index/` is per-device, not synced. Run `embed.py --rebuild` on first use, after restoring from backup, or after migration.

## Project Structure

```
bear-notes/
├── SKILL.md              # Main skill file (conventions + MCP operations)
├── README.md / README.zh-CN.md
├── install.sh            # Multi-agent installer (7 phases)
├── test_memory.py        # Test suite (37 tests)
├── memory/
│   ├── SKILL.md          # Memory sub-skill (proactive protocol + format + operations)
│   ├── embed.py          # Embedding builder + index + migrate-plan
│   ├── search.py         # Semantic search + find-group
│   └── requirements.txt
└── docs/                 # Design documents
```

## Proactive Memory Recall

`install.sh` automatically injects a recall instruction block into each agent's global instruction file:

| Agent | Global Instruction File | Auto-Configured |
|-------|----------------------|-----------------|
| Claude Code | `~/.claude/CLAUDE.md` | ✅ |
| CodeBuddy | `~/.codebuddy/CODEBUDDY.md` | ✅ |
| WorkBuddy | `~/.workbuddy/WORKBUDDY.md` | ✅ |
| Gemini CLI | `~/.gemini/GEMINI.md` | ✅ |
| Copilot CLI | `~/.copilot/instructions.md` | ✅ |
| Codex CLI | `~/.codex/CODEX.md` | ✅ |

The injected block instructs the agent to:
- Recall `#ai/memory/user/entry` and `#ai/memory/feedback/entry` at session start
- Proactively create memories when learning user preferences, corrections, or decisions
- Never wait for the user to say "remember this"

To skip this step: `./install.sh --no-recall`

## Update

The skill is installed as a **symlink** to this repo's `SKILL.md`. To update on any device:

```bash
git pull                 # skill updates immediately via symlink
./install.sh --check     # verify everything is OK
```

### Migration (Old 1:1 Format → Topic Grouped)

```bash
python3 memory/embed.py --migrate-plan   # Phase 1: review grouping plan (read-only)
# → Agent executes plan via MCP         # Phase 2: create topic notes, archive old ones
python3 memory/embed.py --rebuild        # Phase 3: rebuild index
```

## Supported Agents

| Agent | Skill Path | MCP Config | Global Instructions |
|-------|-----------|------------|-------------------|
| Claude Code | `~/.claude/skills/bear-notes/SKILL.md` | `~/.claude.json` | `~/.claude/CLAUDE.md` |
| CodeBuddy | `~/.codebuddy/skills-marketplace/skills/bear-notes/SKILL.md` | `~/.codebuddy/mcp.json` | `~/.codebuddy/CODEBUDDY.md` |
| WorkBuddy | `~/.workbuddy/skills/bear-notes/SKILL.md` | `~/.workbuddy/.mcp.json` | `~/.workbuddy/WORKBUDDY.md` |
| Gemini CLI | `~/.gemini/skills/bear-notes/SKILL.md` | `~/.gemini/settings.json` | `~/.gemini/GEMINI.md` |
| Copilot CLI | `~/.copilot/skills/bear-notes/SKILL.md` | `~/.copilot/config.json` | `~/.copilot/instructions.md` |
| Codex CLI | `~/.codex/skills/bear-notes/SKILL.md` | `~/.codex/mcp.json` | `~/.codex/CODEX.md` |

## Prerequisites

- Bear.app 2.8+ (bundles `bearcli`)
- `bearcli` symlinked to `~/bin/bearcli` (or in PATH)
- Agent must support MCP stdio servers
- Python 3.10+ with `sentence-transformers` and `numpy` for memory system (`pip3 install -r memory/requirements.txt`)
