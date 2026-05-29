# bear-notes

AI agent skill for Bear notes — note writing conventions, MCP CRUD operations, and a persistent memory system. Supports Claude Code, CodeBuddy, WorkBuddy, Gemini CLI, Copilot CLI, and Codex CLI.

## Capabilities

**Note Writing Conventions** — structure template (title + tag on line 2 + body), heading rules (`##`/`###` only), wiki links (`[[Note Title]]`), text formatting, task lists with status checklists, date-prefixed titles (`YYYYMMDD | Title`), blockquote references, footnotes, TagCon icons.

**Tag System Reference** — 7 top-level tags (`#tme`, `#tech`, `#diary`, `#archive`, `#log`, `#read`, `#family`) with a hierarchical assignment protocol that matches content to the deepest applicable leaf tag.

**MCP Operations** — 25 MCP tools via Bear's built-in `bearcli mcp-server`, covering full CRUD, search with Bear's native query syntax, tag/pin/attachment management, and note lifecycle (trash/archive/restore). Safety rules: `overwrite_note` requires `baseHash`, `edit_note` edits are atomic, write-then-verify on every operation.

**Tag Operation Protocol** — safe tag editing via `edit_note` with exact text matching. Never uses `add_tags`/`remove_tags`/`rename_tag`/`delete_tag` (they modify the note body). Three documented cases: migrate tag, add tag to untagged note, remove tag.

**Persistent Memory System** — two-layer storage (index notes + entry notes) for AI agent memories. Four CoALA memory types (user, feedback, project, reference). Semantic search with hybrid ranking (60% similarity + 30% recency + 10% confidence). Cross-agent memory sharing via Bear notes under `#ai/memory`.

## Install

```bash
git clone <repo-url> bear-notes
cd bear-notes
./install.sh
```

Runs 6 phases automatically:
1. Detect installed agents (Claude Code / CodeBuddy / WorkBuddy / Gemini / Copilot / Codex)
2. Check for old versions (backup if found)
3. Install skill via symlink
4. Configure Bear MCP for each agent
5. Install memory system (Python deps + embedding index rebuild)
6. Verify installation and print report

### Options

```
./install.sh              # Auto-detect, install, configure MCP, setup memory, verify
./install.sh --check      # Verify only, no changes
./install.sh --force      # Skip confirmation on old version replacement
./install.sh --no-memory  # Skip memory system setup (pip install + index rebuild)
./install.sh --uninstall  # Remove all symlinks (MCP config preserved)
```

## Memory System

The `memory/` subdirectory provides a persistent memory layer so AI agents can remember across sessions.

| Component | Purpose |
|-----------|---------|
| `memory/SKILL.md` | Memory sub-skill (format spec, classification rules, CRUD operations) |
| `memory/embed.py` | Embedding builder — maintains `~/.bear-memory-index/embeddings.jsonl` |
| `memory/search.py` | Semantic search with hybrid ranking (`0.6×similarity + 0.3×recency + 0.1×confidence`) |
| `memory/requirements.txt` | Python deps: `sentence-transformers>=5.0`, `numpy>=2.0` |

**Memory types:** `user` (who you are, preferences), `feedback` (corrections, behavioral guidance), `project` (deadlines, constraints, decisions), `reference` (external resource pointers).

**Index:** `~/.bear-memory-index/` is per-device, not synced. Run `embed.py --rebuild` on first use or after restoring from backup.

## Project Structure

```
bear-notes/
├── SKILL.md              # Main skill file (conventions + MCP operations)
├── README.md
├── install.sh            # Multi-agent installer
├── memory/
│   ├── SKILL.md          # Memory sub-skill
│   ├── embed.py          # Embedding builder + index maintenance
│   ├── search.py         # Semantic search
│   └── requirements.txt
└── docs/                 # Design documents
```

## Update

The skill is installed as a **symlink** to this repo's `SKILL.md`. To update on any device:

```bash
git pull                 # skill updates immediately via symlink
./install.sh --check     # verify everything is OK
```

## Supported Agents

| Agent | Skill Path | MCP Config |
|-------|-----------|------------|
| Claude Code | `~/.claude/skills/bear-notes/SKILL.md` | `~/.claude.json` |
| CodeBuddy | `~/.codebuddy/skills-marketplace/skills/bear-notes/SKILL.md` | `~/.codebuddy/mcp.json` |
| WorkBuddy | `~/.workbuddy/skills/bear-notes/SKILL.md` | `~/.workbuddy/.mcp.json` |
| Gemini CLI | `~/.gemini/skills/bear-notes/SKILL.md` | `~/.gemini/settings.json` |
| Copilot CLI | `~/.copilot/skills/bear-notes/SKILL.md` | `~/.copilot/config.json` |
| Codex CLI | `~/.codex/skills/bear-notes/SKILL.md` | `~/.codex/mcp.json` |

## Prerequisites

- Bear.app 2.8+ (bundles `bearcli`)
- `bearcli` symlinked to `~/bin/bearcli` (or in PATH)
- Agent must support MCP stdio servers
- Python 3.10+ with `sentence-transformers` and `numpy` for memory system (`pip3 install -r memory/requirements.txt`)
