#!/bin/zsh
set -uo pipefail

SCRIPT_DIR="${0:A:h}"
SKILL_SRC="$SCRIPT_DIR/SKILL.md"
MEMORY_SKILL_SRC="$SCRIPT_DIR/skills/memory/SKILL.md"
GTD_SKILL_SRC="$SCRIPT_DIR/skills/gtd/SKILL.md"
REF_SKILL_SRC="$SCRIPT_DIR/skills/reference/SKILL.md"

# ── OpenClaw 适配 ──────────────────────────────────────────────────
ADAPT_SH="$SCRIPT_DIR/../.shared/adapt-openclaw.sh"
if [[ -f "$ADAPT_SH" ]]; then
  source "$ADAPT_SH"
fi

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
NO_HOOK=false

for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=true ;;
    --uninstall) UNINSTALL=true ;;
    --force) FORCE=true ;;
    --no-memory) NO_MEMORY=true ;;
    --no-recall) NO_RECALL=true ;;
    --no-hook) NO_HOOK=true ;;
    --help|-h)
      echo "Usage: ./install.sh [--check] [--uninstall] [--force] [--no-memory] [--no-recall] [--no-hook]"
      echo "  (no args)  Auto-detect agents, install skill + MCP + memory"
      echo "  --check    Verify only, no changes"
      echo "  --uninstall  Remove all symlinks"
      echo "  --force    Skip confirmation on old version replacement"
      echo "  --no-memory  Skip memory dependencies (pip install + embed rebuild)"
      echo "  --no-recall  Skip global instruction auto-config (Phase Y)"
      echo "  --no-hook    Skip SessionStart hook config (Phase Z2)"
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
  "codex       dir $HOME/.codex $HOME/.codex/skills/bear-notes $HOME/.codex/config.toml toml"
  "openclaw    cmd openclaw $HOME/.openclaw/skills/bear-notes $HOME/.openclaw/openclaw.json openclaw"
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
    openclaw)
      if detect_openclaw && openclaw mcp list 2>/dev/null | grep -q '"bear"'; then
        echo "OK"
      elif declare -f detect_openclaw &>/dev/null && detect_openclaw; then
        echo "FAIL"
      else
        echo "NOCFG"
      fi
      ;;
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
    openclaw)
      if declare -f detect_openclaw &>/dev/null && detect_openclaw; then
        if register_bear_mcp_openclaw; then
          if openclaw mcp list 2>/dev/null | grep -q '"bear"'; then
            echo "OK"
          else
            echo "NEW"
          fi
        else
          echo "FAIL"
        fi
      else
        echo "NOCFG"
      fi
      ;;
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
    if [[ "$name" == "openclaw" ]]; then
      if declare -f detect_openclaw &>/dev/null && detect_openclaw; then
        uninstall_openclaw_skill "bear-notes"
        uninstall_openclaw_skill "bear-memory"
        uninstall_openclaw_skill "bear-gtd"
        uninstall_openclaw_skill "bear-reference"
      fi
      continue
    fi
    agent_installed "$dtype" "$dval" || continue
    target="$sdir/SKILL.md"
    if [[ -L "$target" ]]; then
      rm "$target"
      echo "  $name: removed bear-notes"
    fi
    memory_target="$(dirname "$sdir")/bear-memory/SKILL.md"
    if [[ -L "$memory_target" ]]; then
      rm "$memory_target"
      echo "  $name: removed bear-memory"
    fi
    gtd_target="$(dirname "$sdir")/bear-gtd/SKILL.md"
    if [[ -L "$gtd_target" ]]; then
      rm "$gtd_target"
      echo "  $name: removed bear-gtd"
    fi
    ref_target="$(dirname "$sdir")/bear-reference/SKILL.md"
    if [[ -L "$ref_target" ]]; then
      rm "$ref_target"
      echo "  $name: removed bear-reference"
    fi
  done
  echo "MCP configurations preserved. Remove manually if needed."
  exit 0
fi

# Print header
printf "%-14s %-8s %-8s %-10s %-8s %-8s %-8s %s\n" "Agent" "Skill" "MCP" "bearcli" "Memory" "Gtd" "Ref" "Notes"
printf "%-14s %-8s %-8s %-10s %-8s %-8s %-8s %s\n" "------" "------" "------" "--------" "------" "------" "------" "-----"

installed=0 skipped=0 mcp_ok=0 mcp_new=0

for entry in "${AGENTS[@]}"; do
  read -r name dtype dval sdir mcp fmt <<< "$entry"

  if ! agent_installed "$dtype" "$dval"; then
    printf "%-14s " "$name"; c SKIP; printf " %-8s %-10s %-8s %s\n" "-" "-" "-" "not installed"
    skipped=$((skipped + 1))
    continue
  fi

  # ── OpenClaw 专用安装路径 ──────────────────────────────────────
  if [[ "$name" == "openclaw" ]] && detect_openclaw; then
    if ! $CHECK_ONLY; then
      # 安装 4 个子技能
      adapt_openclaw_skill "$SKILL_SRC"          "$HOME/.openclaw/skills/bear-notes"
      adapt_openclaw_skill "$MEMORY_SKILL_SRC"   "$HOME/.openclaw/skills/bear-memory"
      adapt_openclaw_skill "$GTD_SKILL_SRC"      "$HOME/.openclaw/skills/bear-gtd"
      adapt_openclaw_skill "$REF_SKILL_SRC"      "$HOME/.openclaw/skills/bear-reference"
      # 链接 docs 目录
      install_openclaw_docs "$SCRIPT_DIR/docs" "bear-notes"
      # 注册 Bear MCP
      register_bear_mcp_if_needed
    fi
    # 打印摘要行
    printf "%-14s " "$name"
    c OK; printf " "
    c "$(mcp_status "" openclaw)"
    printf " %-10s" "$bearcli_ok"
    printf " %-8s %-8s %-8s %s\n" "OK" "OK" "OK" "4 sub-skills"
    installed=$((installed + 1))
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

  # Phase 4.5: Install bear-memory skill
  memory_target="$(dirname "$sdir")/bear-memory/SKILL.md"
  memory_status=""
  if ! $CHECK_ONLY && [[ "$skill_status" != "SKIP" ]]; then
    if [[ -L "$memory_target" ]] && [[ "$(readlink "$memory_target")" == "$MEMORY_SKILL_SRC" ]]; then
      memory_status="OK"
    elif [[ -f "$MEMORY_SKILL_SRC" ]]; then
      mkdir -p "$(dirname "$memory_target")"
      ln -sf "$MEMORY_SKILL_SRC" "$memory_target"
      memory_status="NEW"
    fi
  elif $CHECK_ONLY; then
    if [[ -L "$memory_target" ]] && [[ "$(readlink "$memory_target")" == "$MEMORY_SKILL_SRC" ]]; then
      memory_status="OK"
    elif [[ -f "$MEMORY_SKILL_SRC" ]]; then
      memory_status="FAIL"
    else
      memory_status="N/A"
    fi
  else
    memory_status="-"
  fi

  # Phase 4.6: Install bear-gtd skill
  gtd_target="$(dirname "$sdir")/bear-gtd/SKILL.md"
  gtd_status=""
  if ! $CHECK_ONLY && [[ "$skill_status" != "SKIP" ]]; then
    if [[ -L "$gtd_target" ]] && [[ "$(readlink "$gtd_target")" == "$GTD_SKILL_SRC" ]]; then
      gtd_status="OK"
    elif [[ -f "$GTD_SKILL_SRC" ]]; then
      mkdir -p "$(dirname "$gtd_target")"
      ln -sf "$GTD_SKILL_SRC" "$gtd_target"
      gtd_status="NEW"
    fi
  elif $CHECK_ONLY; then
    if [[ -L "$gtd_target" ]] && [[ "$(readlink "$gtd_target")" == "$GTD_SKILL_SRC" ]]; then
      gtd_status="OK"
    elif [[ -f "$GTD_SKILL_SRC" ]]; then
      gtd_status="FAIL"
    else
      gtd_status="N/A"
    fi
  else
    gtd_status="-"
  fi

  # Phase 4.7: Install bear-reference skill
  ref_target="$(dirname "$sdir")/bear-reference/SKILL.md"
  ref_status=""
  if ! $CHECK_ONLY && [[ "$skill_status" != "SKIP" ]]; then
    if [[ -L "$ref_target" ]] && [[ "$(readlink "$ref_target")" == "$REF_SKILL_SRC" ]]; then
      ref_status="OK"
    elif [[ -f "$REF_SKILL_SRC" ]]; then
      mkdir -p "$(dirname "$ref_target")"
      ln -sf "$REF_SKILL_SRC" "$ref_target"
      ref_status="NEW"
    fi
  elif $CHECK_ONLY; then
    if [[ -L "$ref_target" ]] && [[ "$(readlink "$ref_target")" == "$REF_SKILL_SRC" ]]; then
      ref_status="OK"
    elif [[ -f "$REF_SKILL_SRC" ]]; then
      ref_status="FAIL"
    else
      ref_status="N/A"
    fi
  else
    ref_status="-"
  fi

  # Print row
  printf "%-14s " "$name"
  c "${skill_status:-FAIL}"
  printf " "
  c "${mcp_result:--}"
  printf " "
  c "$bearcli_ok"
  printf " "
  c "${memory_status:--}"
  printf " "
  c "${gtd_status:--}"; printf " "; c "${ref_status:--}"
  printf " %s\n" "${skill_note:-}"

  installed=$((installed + 1))
  case "$mcp_result" in
    OK) mcp_ok=$((mcp_ok + 1)) ;;
    NEW|UPD) mcp_new=$((mcp_new + 1)) ;;
  esac
done

# ── OpenClaw: 如有新 MCP 注册则重启 Gateway ──────────────────────
if declare -f restart_gateway_if_mcp_changed &>/dev/null; then
  restart_gateway_if_mcp_changed
fi

# ── Phase W: Firecrawl MCP auto-config ────────────────────────────
firecrawl_status=""
if ! $CHECK_ONLY; then
  echo ""
  echo "--- Firecrawl MCP ---"
  if npx -y firecrawl-mcp --help &>/dev/null; then
    echo "  firecrawl-mcp: available"
    # Check if already configured in ~/.claude.json
    if python3 -c "
import json, sys
try:
    with open('$HOME/.claude.json') as f:
        cfg = json.load(f)
    servers = cfg.get('mcpServers', {})
    if 'firecrawl' in servers:
        sys.exit(0)
    else:
        sys.exit(1)
except Exception: sys.exit(1)
" 2>/dev/null; then
      echo "  MCP config: already in ~/.claude.json"
      firecrawl_status="OK"
    else
      echo "  MCP config: adding to ~/.claude.json..."
      python3 << 'PYEOF'
import json, os
home = os.path.expanduser("~")
with open(f"{home}/.claude.json") as f:
    cfg = json.load(f)
cfg.setdefault("mcpServers", {})["firecrawl"] = {
    "command": "npx",
    "args": ["-y", "firecrawl-mcp"],
}
with open(f"{home}/.claude.json", "w") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
print("  MCP config: added firecrawl (restart session to activate)")
PYEOF
      firecrawl_status="NEW"
    fi
    # Check for API key — try env first, then ~/.zshrc, then prompt
    if [[ -n "${FIRECRAWL_API_KEY:-}" ]]; then
      echo "  API key: configured (from environment)"
    else
      # Check if already saved in ~/.zshrc
      _saved_key=$(grep -o 'FIRECRAWL_API_KEY="[^"]*"' "$HOME/.zshrc" 2>/dev/null | head -1)
      if [[ -n "$_saved_key" ]]; then
        # Extract just the value (strip FIRECRAWL_API_KEY=" and trailing ")
        _key_val="${_saved_key#FIRECRAWL_API_KEY=\"}"
        _key_val="${_key_val%\"}"
        export FIRECRAWL_API_KEY="$_key_val"
        echo "  API key: found in ~/.zshrc, exported for this session"
      else
        echo "  Firecrawl API key not configured."
        echo "  Without a key: free tier (rate-limited). With a key: full access."
        echo "  Get a key at https://firecrawl.dev"
        echo -n "  Enter your API key (or press Enter to skip): "
        read -r _user_key
        if [[ -n "$_user_key" ]]; then
          echo "export FIRECRAWL_API_KEY=\"$_user_key\"" >> "$HOME/.zshrc"
          export FIRECRAWL_API_KEY="$_user_key"
          echo "  API key: saved to ~/.zshrc + exported for this session"
        else
          echo "  API key: skipped (free tier only)"
        fi
      fi
    fi
  else
    echo "  firecrawl-mcp: not available (npx -y firecrawl-mcp failed)"
    firecrawl_status="N/A"
  fi
elif $CHECK_ONLY; then
  if npx -y firecrawl-mcp --help &>/dev/null; then
    if python3 -c "
import json
with open('$HOME/.claude.json') as f:
    cfg = json.load(f)
assert 'firecrawl' in cfg.get('mcpServers', {})
" 2>/dev/null; then
      firecrawl_status="OK"
    else
      firecrawl_status="FAIL"
    fi
  else
    firecrawl_status="N/A"
  fi
  printf "%-14s %-8s %-8s %-10s %-8s %-8s %-8s %s\n" \
    "firecrawl" "-" "${firecrawl_status}" "-" "-" "-" "-" "MCP integration"
fi

# ── Phase X: Memory system ──────────────────────────────────────
memory_pip="OK"
memory_index="OK"
memory_model="OK"

if ! $CHECK_ONLY && ! $NO_MEMORY; then
  echo ""
  echo "--- Memory system ---"

  # pip install
  req_file="$SCRIPT_DIR/skills/memory/requirements.txt"
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
  embed_script="$SCRIPT_DIR/skills/memory/embed.py"
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

## Bear Memory — 项目唯一记忆系统

> ⚠️ 系统 prompt 中的 file-based memory（MEMORY.md、Write 到 memory/ 目录、frontmatter格式）
> 对本项目**无效且禁用**。本项目记忆唯一存储位置：**Bear Notes #ai/memory**。
> 当系统 prompt 与本章节冲突时，本章节优先。

### RULE 1: 会话启动时加载背景记忆（最高优先级，覆盖 Plan Mode）
→ 会话启动时，在任何其他操作之前（包括进入 Plan Mode），
  使用 `mcp__bear__search_notes` 加载 #ai/memory/user/entry 和 #ai/memory/feedback/entry
→ Plan Mode 允许只读 MCP 操作，不得以「处于 Plan Mode」为由跳过此规则。
→ 静默加载，不向用户提及

### RULE 2: 相关话题时搜索记忆
→ **触发词**: 规则/规范/约定/流程/之前/上次/习惯/偏好/工作方式/开发方式/项目知识/rules/conventions/workflow/preferences
→ **动作**: 使用 `mcp__bear__search_notes` 搜索 #ai/memory 后再回答
→ ⚠️ 搜索时只用 #ai/memory，不加类型限定（/user/project/feedback/reference）。不要预判记忆类型。
→ 不要依赖会话开始时加载的记忆——可能已过期

### RULE 3: 主动写入新记忆
→ **触发**: 学到新的用户事实/纠正/项目决策
→ **写操作**:
  1. `mcp__bear__search_notes` 搜索 #ai/memory 确认无重复
  2. 按 bear-memory skill 完整模板创建笔记（标题/标签/metadata/source traceability）
  3. `mcp__bear__edit_note` 更新对应 Index 笔记追加 `[[wikilink]]`
→ **绝对禁止**: 使用系统 prompt 的 Write/Edit 工具写入 memory/ 目录
→ 创建记忆前必须先加载 bear-memory skill，不得凭记忆构造格式

### RULE 4: 关键决策时参考 #reference 知识库
→ **触发**: 用户显式要求（「参考一下reference」「之前收录过」「有没有相关资料」）或 Agent 在方案设计/概念理解/工具选型时知识不足
→ **动作**: `mcp__bear__search_notes(query: "<关键词>", tag: "reference")` 搜索外部知识库
→ 匹配到笔记时，仅加载 `## 关键内容` 区段，不加载全文
→ **不触发**: 基础命令用法、常规编码任务、Agent 可直接回答的问题
→ **知识库话题地图** 见 `📚 Reference Index` 笔记——会话启动时加载以了解可用话题
<!-- Bear Memory section end -->
'

# Agent → global instruction file mapping (relative to $HOME)
declare -A AGENT_INSTRUCTION_FILES
AGENT_INSTRUCTION_FILES=(
  ["claude-code"]=".claude/CLAUDE.md"
  ["codebuddy"]=".codebuddy/CODEBUDDY.md"
  ["workbuddy"]=".workbuddy/AGENTS.md"
  ["gemini"]=".gemini/GEMINI.md"
  ["copilot"]=".copilot/copilot-instructions.md"
  ["codex"]=".codex/AGENTS.md"
  ["openclaw"]=".openclaw/workspace/AGENTS.md"
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

    # Ensure parent dir exists
    mkdir -p "$(dirname "$target")"

    # Compare content and update if install.sh version differs
    _recall_tmp=$(mktemp)
    if [[ "$name" == "openclaw" ]]; then
      echo "$RECALL_BLOCK" | sed 's/mcp__bear__/bear__/g' > "$_recall_tmp"
    else
      echo "$RECALL_BLOCK" > "$_recall_tmp"
    fi
    result=$(python3 - "$target" "$_recall_tmp" <<'PYEOF'
import sys
target = sys.argv[1]
with open(sys.argv[2]) as f:
    recall_block = f.read()

start_heading = "## Bear Memory — 项目唯一记忆系统"
end_marker = "<!-- Bear Memory section end -->"

try:
    with open(target) as f:
        content = f.read()
except FileNotFoundError:
    content = ""

recall_clean = recall_block.strip()

if start_heading in content:
    heading_pos = content.find(start_heading)

    # Search backwards for "---" separator (within 500 chars)
    search_start = max(0, heading_pos - 500)
    prefix = content[search_start:heading_pos]
    sep_pos = prefix.rfind('\n---\n')
    if sep_pos != -1:
        section_start = search_start + sep_pos + 1
    else:
        section_start = heading_pos

    # Find end marker
    if end_marker in content[section_start:]:
        end_pos = content.find(end_marker, section_start)
        line_end = content.find('\n', end_pos)
        section_end = line_end + 1 if line_end != -1 else len(content)
    else:
        section_end = len(content)

    existing = content[section_start:section_end].strip()

    if existing == recall_clean:
        print("OK")
    else:
        new_content = content[:section_start] + recall_block + content[section_end:]
        with open(target, 'w') as f:
            f.write(new_content)
        print("UPD")
else:
    if content and not content.endswith('\n'):
        content += '\n'
    with open(target, 'w') as f:
        f.write(content + recall_block)
    print("NEW")
PYEOF
)
    rm -f "$_recall_tmp"

    case "$result" in
      OK)  echo "  $name: up-to-date ($instr_file)" ;;
      UPD) echo "  $name: updated ($instr_file)" ;;
      NEW) echo "  $name: created ($instr_file)" ;;
      *)   echo "  $name: error ($instr_file)" ;;
    esac
    auto_config_count=$((auto_config_count + 1))
  done

  if [[ $auto_config_count -eq 0 ]]; then
    echo "  (no agents with global instruction support detected)"
  fi
elif $CHECK_ONLY; then
  echo ""
  echo "--- Global instruction check ---"

  for entry in "${AGENTS[@]}"; do
    read -r name dtype dval sdir mcp fmt <<< "$entry"
    agent_installed "$dtype" "$dval" || continue

    instr_file="${AGENT_INSTRUCTION_FILES[$name]}"
    [[ -z "$instr_file" ]] && continue
    target="$HOME/$instr_file"

    if [[ ! -f "$target" ]]; then
      echo "  $name: no instruction file ($instr_file)"
      continue
    fi

    _recall_tmp=$(mktemp)
    if [[ "$name" == "openclaw" ]]; then
      echo "$RECALL_BLOCK" | sed 's/mcp__bear__/bear__/g' > "$_recall_tmp"
    else
      echo "$RECALL_BLOCK" > "$_recall_tmp"
    fi
    check_result=$(python3 - "$target" "$_recall_tmp" "check" <<'PYEOF'
import sys
target = sys.argv[1]
with open(sys.argv[2]) as f:
    recall_block = f.read()

start_heading = "## Bear Memory — 项目唯一记忆系统"
end_marker = "<!-- Bear Memory section end -->"

with open(target) as f:
    content = f.read()

recall_clean = recall_block.strip()

if start_heading in content:
    heading_pos = content.find(start_heading)
    search_start = max(0, heading_pos - 500)
    prefix = content[search_start:heading_pos]
    sep_pos = prefix.rfind('\n---\n')
    if sep_pos != -1:
        section_start = search_start + sep_pos + 1
    else:
        section_start = heading_pos

    if end_marker in content[section_start:]:
        end_pos = content.find(end_marker, section_start)
        line_end = content.find('\n', end_pos)
        section_end = line_end + 1 if line_end != -1 else len(content)
    else:
        section_end = len(content)

    existing = content[section_start:section_end].strip()

    if existing == recall_clean:
        print("OK")
    else:
        print("UPD")
else:
    print("NEW")
PYEOF
)
    rm -f "$_recall_tmp"

    case "$check_result" in
      OK)  echo "  $name: up-to-date ($instr_file)" ;;
      UPD) echo "  $name: outdated ($instr_file)" ;;
      NEW) echo "  $name: missing ($instr_file)" ;;
      *)   echo "  $name: unknown ($instr_file)" ;;
    esac
    auto_config_count=$((auto_config_count + 1))
  done
fi

# ── Phase Z: MCP permission auto-config ───────────────────────────
# Adds common read-only Bear MCP operations to the project's
# .claude/settings.local.json to reduce permission prompts.
# Idempotent — skips entries already present.

BEAR_MCP_ALLOWLIST=(
  "mcp__bear__search_notes"
  "mcp__bear__get_note"
  "mcp__bear__read_note_content"
  "mcp__bear__search_in_note"
  "mcp__bear__list_tags"
  "mcp__bear__list_notes"
  "mcp__bear__list_attachments"
  "mcp__bear__append_to_note"
  "mcp__bear__archive_note"
  "mcp__bear__restore_note"
  "mcp__bear__open_note"
  "mcp__bear__edit_note"
  "mcp__bear__create_note"
  "mcp__bear__overwrite_note"
  "mcp__bear__trash_note"
)

SETTINGS_FILE="$SCRIPT_DIR/.claude/settings.local.json"

if ! $CHECK_ONLY; then
  echo ""
  echo "--- MCP permission auto-config ---"

  # Create or load settings file
  if [[ -f "$SETTINGS_FILE" ]]; then
    # Parse existing allow list
    existing=$(python3 -c "
import json
with open('$SETTINGS_FILE') as f:
    cfg = json.load(f)
for item in cfg.get('permissions',{}).get('allow',[]):
    print(item)
" 2>/dev/null)
  else
    mkdir -p "$(dirname "$SETTINGS_FILE")"
    echo '{"permissions":{"allow":[]}}' > "$SETTINGS_FILE"
    existing=""
  fi

  added=0 mcp_skipped=0
  for entry in "${BEAR_MCP_ALLOWLIST[@]}"; do
    if echo "$existing" | grep -qF "$entry" 2>/dev/null; then
      mcp_skipped=$((mcp_skipped + 1))
    else
      # Append to allow array
      python3 -c "
import json
with open('$SETTINGS_FILE') as f:
    cfg = json.load(f)
cfg.setdefault('permissions',{}).setdefault('allow',[]).append('$entry')
with open('$SETTINGS_FILE','w') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
    f.write('\n')
" 2>/dev/null && added=$((added + 1))
    fi
  done

  echo "  Bear MCP: $added added, $mcp_skipped already configured"
else
  echo ""
  echo "--- MCP permission check (read-only) ---"
  if [[ -f "$SETTINGS_FILE" ]]; then
    configured=$(python3 -c "
import json
with open('$SETTINGS_FILE') as f:
    cfg = json.load(f)
allow = cfg.get('permissions',{}).get('allow',[])
missing = [e for e in ['mcp__bear__search_notes','mcp__bear__get_note','mcp__bear__read_note_content'] if e not in allow]
print(len(allow) if not missing else 'MISSING: ' + ', '.join(missing))
")
    echo "  Bear MCP: $configured"
  else
    echo "  Bear MCP: no settings file"
  fi
fi

# ── Phase Z2: SessionStart hook (Claude Code only) ─────────────────
hook_configured=0
if ! $CHECK_ONLY && ! $NO_HOOK; then
  echo ""
  echo "--- SessionStart hook ---"

  cc_settings="$HOME/.claude/settings.json"
  recall_script="$SCRIPT_DIR/skills/memory/recall.py"

  python3 - "$cc_settings" "$recall_script" <<'PYEOF'
import json, sys

settings_file = sys.argv[1]
recall_path = sys.argv[2]
recall_command = f"python3 {recall_path}"

try:
    with open(settings_file) as f:
        config = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    config = {}

if "hooks" not in config:
    config["hooks"] = {}

existing = config["hooks"].get("SessionStart", [])
already_configured = any(recall_command in json.dumps(h) for h in existing)

if already_configured:
    print("  Claude Code: SessionStart hook already configured")
    sys.exit(0)

new_hook = {
    "matcher": "startup",
    "hooks": [{"type": "command", "command": recall_command}]
}
config["hooks"]["SessionStart"] = existing + [new_hook]

with open(settings_file, "w") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)
    f.write("\n")

print("  Claude Code: SessionStart hook configured -> recall.py")
PYEOF
  hook_configured=$?
elif $CHECK_ONLY; then
  cc_settings="$HOME/.claude/settings.json"
  recall_script="$SCRIPT_DIR/skills/memory/recall.py"
  if python3 -c "
import json, sys
try:
    with open('$cc_settings') as f: cfg = json.load(f)
    for h in cfg.get('hooks',{}).get('SessionStart',[]):
        if 'recall.py' in json.dumps(h): sys.exit(0)
    sys.exit(1)
except Exception: sys.exit(1)
" 2>/dev/null; then
    echo "  Claude Code: SessionStart hook already configured"
  else
    echo "  Claude Code: SessionStart hook not configured"
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
echo -e "Hook:    SessionStart $([ $hook_configured -eq 0 ] && echo 'configured' || echo 'skipped')"
