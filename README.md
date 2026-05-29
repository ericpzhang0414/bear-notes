# bear-notes

AI agent skill for Bear notes — content conventions and MCP operations.

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
5. Verify installation
6. Print report

### Options

```
./install.sh            # Auto-detect, install, configure MCP, verify
./install.sh --check    # Verify only, no changes
./install.sh --force    # Skip confirmation on old version replacement
./install.sh --uninstall # Remove all symlinks (MCP config preserved)
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
