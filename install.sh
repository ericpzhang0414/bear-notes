#!/bin/zsh
set -uo pipefail

SCRIPT_DIR="${0:A:h}"
SKILL_SRC="$SCRIPT_DIR/SKILL.md"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

CHECK_ONLY=false
UNINSTALL=false
FORCE=false
NO_MEMORY=false
NO_RECALL=false

for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=true ;;
    --uninstall) UNINSTALL=true ;;
    --force) FORCE=true ;;
    --no-memory) NO_MEMORY=true ;;
    --no-recall) NO_RECALL=true ;;
    --help|-h)
      echo "Usage: ./install.sh [--check] [--uninstall] [--force] [--no-memory]"
      echo "  (no args)  Auto-detect agents, install skill + MCP + memory"
      echo "  --check    Verify only, no changes"
      echo "  --uninstall  Remove all symlinks"
      echo "  --force    Skip confirmation on old version replacement"
      echo "  --no-memory  Skip memory dependencies (pip install + embed rebuild)"
      exit 0 ;;
    *) echo "Unknown: $arg"; exit 1 ;;
  esac
done

# ── Agent Registry ──────────────────────────────────────────────
# name detect_type detect_value skill_dir mcp_file [mcp_format]
#   mcp_format: "" (standard JSON), "copilot" (JSON +type +tools), "toml" (TOML)
AGENTS=(
  "claude-code dir $HOME/.claude $HOME/.claude/skills/bear-notes $HOME/.claude.json"
  "codebuddy   dir $HOME/.codebuddy $HOME/.codebuddy/skills-marketplace/skills/bear-notes $HOME/.codebuddy/mcp.json"
  "workbuddy   dir $HOME/.workbuddy $HOME/.workbuddy/skills/bear-notes $HOME/.workbuddy/mcp.json"
  "gemini      cmd gemini $HOME/.gemini/skills/bear-notes $HOME/.gemini/settings.json"
  "copilot     cmd copilot $HOME/.copilot/skills/bear-notes $HOME/.copilot/mcp-config.json copilot"
  "codex       cmd codex $HOME/.codex/skills/bear-notes $HOME/.codex/config.toml toml"
)

# ── Color helpers ────────────────────────────────────────────────
c() {
  case "$1" in
    OK)   echo -n "${GREEN}[OK]${NC}" ;;
    FAIL) echo -n "${RED}[FAIL]${NC}" ;;
    NEW)  echo -n "${GREEN}[NEW]${NC}" ;;
    UPD)  echo -n "${YELLOW}[UPD]${NC}" ;;
    SKIP) echo -n "${CYAN}[SKIP]${NC}" ;;
    MISS) echo -n "${RED}[MISS]${NC}" ;;
    NOCFG) echo -n "${RED}[NOCFG]${NC}" ;;
    *)    echo -n "$1" ;;
  esac
}

# ── Agent detection ──────────────────────────────────────────────
# returns 0 if agent is installed
agent_installed() {
  case "$1" in
    dir) [[ -d "$2" ]] ;;
    cmd) command -v "$2" &>/dev/null ;;
  esac
}

# ── MCP config helper ────────────────────────────────────────────
# $1 = mcp file path, $2 = format ("" = standard JSON, "copilot", "toml")
mcp_status() {
  case "${2:-}" in
    toml)
      # TOML: check [mcp_servers.bear] section exists with correct command
      if [[ -f "$1" ]]; then
        if grep -q '^\[mcp_servers\.bear\]$' "$1" 2>/dev/null && \
           grep -Fq "command = \"$BEARCLI_CMD\"" "$1" 2>/dev/null && \
           grep -q '^args = \["mcp-server"\]$' "$1" 2>/dev/null; then
          echo "OK"
        else
          echo "FAIL"
        fi
      else
        echo "NOCFG"
      fi
      ;;
    copilot)
      python3 -c "
import json, os
try:
    with open('$1') as f: c = json.load(f)
    b = c.get('mcpServers',{}).get('bear',{})
    bearcli = os.environ.get('BEARCLI_CMD', 'bearcli')
    ok = (b.get('type')=='local' and b.get('command')==bearcli
          and b.get('args')==['mcp-server'] and b.get('tools')==['*'])
    print('OK' if ok else 'FAIL')
except: print('NOCFG')
"
      ;;
    *)
      python3 -c "
import json, os
try:
    with open('$1') as f: c = json.load(f)
    b = c.get('mcpServers',{}).get('bear',{})
    bearcli = os.environ.get('BEARCLI_CMD', 'bearcli')
    ok = (b.get('command')==bearcli and b.get('args')==['mcp-server'])
    print('OK' if ok else 'FAIL')
except: print('NOCFG')
"
      ;;
  esac
}

mcp_configure() {
  case "${2:-}" in
    toml)
      if [[ -f "$1" ]]; then
        if grep -q '^\[mcp_servers\.bear\]$' "$1" 2>/dev/null && \
           grep -Fq "command = \"$BEARCLI_CMD\"" "$1" 2>/dev/null && \
           grep -q '^args = \["mcp-server"\]$' "$1" 2>/dev/null; then
          echo "OK"
        else
          # Append to existing TOML file
          printf '\n[mcp_servers.bear]\ncommand = "%s"\nargs = ["mcp-server"]\n' "$BEARCLI_CMD" >> "$1"
          echo "NEW"
        fi
      else
        # Create new TOML file
        mkdir -p "$(dirname "$1")"
        printf '[mcp_servers.bear]\ncommand = "%s"\nargs = ["mcp-server"]\n' "$BEARCLI_CMD" > "$1"
        echo "NEW"
      fi
      ;;
    copilot)
      python3 - "$1" <<'PYEOF'
import sys, json, os
mcp_file = sys.argv[1]
bearcli = os.environ.get("BEARCLI_CMD", "bearcli")
try:
    with open(mcp_file) as f: config = json.load(f)
except: config = {}

existing = config.get("mcpServers", {}).get("bear", {})
correct = {"type": "local", "command": bearcli, "args": ["mcp-server"], "tools": ["*"]}
if existing == correct:
    print("OK")
else:
    status = "UPD" if existing else "NEW"
    config.setdefault("mcpServers", {})["bear"] = correct
    with open(mcp_file, "w") as f: json.dump(config, f, indent=2, ensure_ascii=False)
    print(status)
PYEOF
      ;;
    *)
      python3 - "$1" <<'PYEOF'
import sys, json, os
mcp_file = sys.argv[1]
bearcli = os.environ.get("BEARCLI_CMD", "bearcli")
try:
    with open(mcp_file) as f: config = json.load(f)
except: config = {}

existing = config.get("mcpServers", {}).get("bear", {})
correct = {"command": bearcli, "args": ["mcp-server"]}
if existing == correct:
    print("OK")
else:
    status = "UPD" if existing else "NEW"
    config.setdefault("mcpServers", {})["bear"] = correct
    with open(mcp_file, "w") as f: json.dump(config, f, indent=2, ensure_ascii=False)
    print(status)
PYEOF
      ;;
  esac
}

# ── Resolve bearcli path ─────────────────────────────────────────
# Claude Code / MCP clients spawn processes directly (not via shell),
# so shell aliases (Bear's default) won't work. We need the real path.
resolve_bearcli() {
  # 1. Check zsh alias (Bear's default install method)
  if [[ -n "${aliases[bearcli]:-}" ]]; then
    local p="${aliases[bearcli]}"
    [[ -x "$p" ]] && echo "$p" && return 0
  fi
  # 2. Check PATH for a real binary
  local p
  p=$(whence -p bearcli 2>/dev/null)
  if [[ -n "$p" ]] && [[ -x "$p" ]]; then
    echo "$p" && return 0
  fi
  # 3. Check standard Bear macOS location
  local std="/Applications/Bear.app/Contents/MacOS/bearcli"
  if [[ -x "$std" ]]; then
    echo "$std" && return 0
  fi
  # 4. Not found — fall back to bare name
  echo "bearcli"
  return 1
}

BEARCLI_CMD=$(resolve_bearcli) || true
export BEARCLI_CMD

bearcli_ok="OK"
[[ -x "$BEARCLI_CMD" ]] || bearcli_ok="MISS"

echo "=== bear-notes skill installer ==="
echo "Source: $SKILL_SRC"
echo ""

if $UNINSTALL; then
  echo "Removing bear-notes symlinks..."
  for entry in "${AGENTS[@]}"; do
    read -r name dtype dval sdir mcp fmt <<< "$entry"
    agent_installed "$dtype" "$dval" || continue
    target="$sdir/SKILL.md"
    if [[ -L "$target" ]]; then
      rm "$target"
      echo "  $name: removed symlink"
    fi
  done
  echo "MCP configurations preserved. Remove manually if needed."
  exit 0
fi

# Print header
printf "%-14s %-8s %-8s %-10s %s\n" "Agent" "Skill" "MCP" "bearcli" "Notes"
printf "%-14s %-8s %-8s %-10s %s\n" "------" "------" "------" "--------" "-----"

installed=0 skipped=0 mcp_ok=0 mcp_new=0

for entry in "${AGENTS[@]}"; do
  read -r name dtype dval sdir mcp fmt <<< "$entry"

  if ! agent_installed "$dtype" "$dval"; then
    printf "%-14s " "$name"; c SKIP; printf " %-8s %-10s %s\n" "-" "-" "not installed"
    skipped=$((skipped + 1))
    continue
  fi

  target="$sdir/SKILL.md"
  skill_status="" skill_note=""

  # Phase 2: Check existing
  if [[ -L "$target" ]] && [[ "$(readlink "$target")" == "$SKILL_SRC" ]]; then
    skill_status="OK"
    skill_note="up-to-date"
  elif [[ -L "$target" ]]; then
    skill_note="old symlink → $(readlink "$target")"
  elif [[ -d "$target" ]]; then
    skill_note="old CLI skill (directory)"
  elif [[ -f "$target" ]]; then
    skill_note="old standalone file"
  elif [[ -e "$target" ]]; then
    skill_note="unknown existing"
  fi

  # Phase 3: Install (unless check-only)
  if ! $CHECK_ONLY && [[ "$skill_status" != "OK" ]]; then
    # Backup old versions
    if [[ -n "$skill_note" ]]; then
      if ! $FORCE; then
        echo -e "${YELLOW}[WARN] $name: $skill_note${NC}"
        echo "        Replace with symlink? [y/N] "
        read -r answer
        [[ "$answer" =~ ^[Yy] ]] || { skill_status="SKIP"; }
      else
        echo -e "${YELLOW}[WARN] $name: $skill_note (--force)${NC}"
      fi
      if [[ "$skill_status" != "SKIP" ]]; then
        bak="${sdir}.bak"
        [[ -e "$bak" ]] && rm -rf "$bak"
        mv "$target" "$bak" 2>/dev/null || rm -rf "$target"
        skill_note="old → backed up"
      fi
    fi
    if [[ "$skill_status" != "SKIP" ]]; then
      mkdir -p "$sdir"
      ln -sf "$SKILL_SRC" "$target"
      skill_status="OK"
    fi
  elif $CHECK_ONLY; then
    [[ -z "$skill_status" ]] && skill_status="FAIL"
  fi

  # Phase 4: Configure MCP (unless check-only)
  mcp_result="-"
  if ! $CHECK_ONLY && [[ "$skill_status" != "SKIP" ]]; then
    mcp_result=$(mcp_configure "$mcp" "$fmt")
  elif $CHECK_ONLY; then
    mcp_result=$(mcp_status "$mcp" "$fmt")
  fi

  # Verify symlink
  if [[ -L "$target" ]] && [[ "$(readlink "$target")" == "$SKILL_SRC" ]]; then
    skill_status="OK"
  fi

  # Print row
  printf "%-14s " "$name"
  c "${skill_status:-FAIL}"
  printf " "
  c "${mcp_result:--}"
  printf " "
  c "$bearcli_ok"
  printf " %s\n" "${skill_note:-}"

  installed=$((installed + 1))
  case "$mcp_result" in
    OK) mcp_ok=$((mcp_ok + 1)) ;;
    NEW|UPD) mcp_new=$((mcp_new + 1)) ;;
  esac
done

# ── Phase X: Memory system ──────────────────────────────────────
memory_pip="OK"
memory_index="OK"
memory_model="OK"

if ! $CHECK_ONLY && ! $NO_MEMORY; then
  echo ""
  echo "--- Memory system ---"

  # pip install
  req_file="$SCRIPT_DIR/memory/requirements.txt"
  if [[ -f "$req_file" ]]; then
    if python3 -c "import sentence_transformers" &>/dev/null; then
      echo "  pip deps: already installed"
    else
      echo "  pip deps: installing..."
      if python3 -m pip install -r "$req_file" --quiet 2>&1; then
        memory_pip="NEW"
        echo "  pip deps: installed"
      else
        memory_pip="FAIL"
        echo "  pip deps: FAILED"
      fi
    fi
  else
    memory_pip="N/A"
  fi

  # Index directory
  index_dir="$HOME/.bear-memory-index"
  if [[ -d "$index_dir" ]]; then
    echo "  index dir: $index_dir"
  else
    mkdir -p "$index_dir"
    echo "  index dir: created $index_dir"
  fi

  # embed rebuild
  embed_script="$SCRIPT_DIR/memory/embed.py"
  if [[ -f "$embed_script" ]]; then
    echo "  embed rebuild: running..."
    if python3 "$embed_script" --rebuild 2>&1; then
      echo "  embed rebuild: OK"
    else
      memory_index="FAIL"
      echo "  embed rebuild: FAILED"
    fi
  else
    memory_index="N/A"
  fi
fi

# ── Phase Y: Global instruction auto-config ────────────────────────
# Injects memory auto-recall block into each agent's global instruction
# file (e.g., ~/.claude/CLAUDE.md). Idempotent — skips if already present.

RECALL_BLOCK='
---

## Bear Memory — MUST FOLLOW ALL 3 RULES

### RULE 1: Recall at Session Start
→ Use search_notes tool to load #ai/memory/user/entry
  and #ai/memory/feedback/entry silently.

### RULE 2: Search Before Answering
→ TRIGGER: User mentions 规则/规范/约定/流程/之前/上次/
  习惯/偏好/工作方式/开发方式/项目知识/rules/conventions/
  workflow/preferences
→ ACTION: Use search_notes tool to search #ai/memory BEFORE answering.
  Do NOT rely on preloaded memories — they may have expired.

### RULE 3: Write New Memories Proactively
→ TRIGGER: Learn new user fact / correction / project decision
→ ACTION: Create note under #ai/memory/<type>/entry in Bear.
        NEVER use built-in agent memory for this.
        Full protocol: see bear-memory skill.
'

# Agent → global instruction file mapping (relative to $HOME)
declare -A AGENT_INSTRUCTION_FILES
AGENT_INSTRUCTION_FILES=(
  ["claude-code"]=".claude/CLAUDE.md"
  ["codebuddy"]=".codebuddy/CODEBUDDY.md"
  ["workbuddy"]=".workbuddy/WORKBUDDY.md"
  ["gemini"]=".gemini/GEMINI.md"
  ["copilot"]=".copilot/instructions.md"
  ["codex"]=".codex/CODEX.md"
)

auto_config_count=0
if ! $CHECK_ONLY && ! $NO_RECALL; then
  echo ""
  echo "--- Global instruction auto-config ---"

  for entry in "${AGENTS[@]}"; do
    read -r name dtype dval sdir mcp fmt <<< "$entry"
    agent_installed "$dtype" "$dval" || continue

    instr_file="${AGENT_INSTRUCTION_FILES[$name]}"
    [[ -z "$instr_file" ]] && continue
    target="$HOME/$instr_file"

    # Check if recall block already present
    if [[ -f "$target" ]] && grep -q "NEVER use built-in agent memory" "$target" 2>/dev/null; then
      echo "  $name: already configured ($instr_file)"
      auto_config_count=$((auto_config_count + 1))
      continue
    fi

    # Create parent dir if needed
    mkdir -p "$(dirname "$target")"

    # Append (or create) the instruction file
    if [[ -f "$target" ]]; then
      echo "$RECALL_BLOCK" >> "$target"
      echo "  $name: appended to $instr_file"
    else
      # New file: add a header line
      echo "# $name global instructions" > "$target"
      echo "$RECALL_BLOCK" >> "$target"
      echo "  $name: created $instr_file"
    fi
    auto_config_count=$((auto_config_count + 1))
  done

  if [[ $auto_config_count -eq 0 ]]; then
    echo "  (no agents with global instruction support detected)"
  fi
fi

echo ""
echo -e "Summary: ${GREEN}$installed installed${NC}, $skipped skipped (not detected)"
echo -e "MCP:     $mcp_ok already configured, $mcp_new newly configured"
if ! $NO_MEMORY; then
  printf "Memory:  pip: "; c "$memory_pip"
  printf "  index: "; c "$memory_index"
  echo ""
fi
echo -e "Recall:  $auto_config_count agents configured"
