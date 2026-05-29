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

for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=true ;;
    --uninstall) UNINSTALL=true ;;
    --force) FORCE=true ;;
    --help|-h)
      echo "Usage: ./install.sh [--check] [--uninstall] [--force]"
      exit 0 ;;
    *) echo "Unknown: $arg"; exit 1 ;;
  esac
done

# ── Agent Registry ──────────────────────────────────────────────
# name detect_type detect_value skill_dir mcp_file
AGENTS=(
  "claude-code dir $HOME/.claude $HOME/.claude/skills/bear-notes $HOME/.claude.json"
  "codebuddy   dir $HOME/.codebuddy $HOME/.codebuddy/skills-marketplace/skills/bear-notes $HOME/.codebuddy/mcp.json"
  "workbuddy   dir $HOME/.workbuddy $HOME/.workbuddy/skills/bear-notes $HOME/.workbuddy/.mcp.json"
  "gemini      cmd gemini $HOME/.gemini/skills/bear-notes $HOME/.gemini/settings.json"
  "copilot     cmd copilot $HOME/.copilot/skills/bear-notes $HOME/.copilot/config.json"
  "codex       cmd codex $HOME/.codex/skills/bear-notes $HOME/.codex/mcp.json"
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
mcp_status() {
  python3 -c "
import json
try:
    with open('$1') as f: c = json.load(f)
    b = c.get('mcpServers',{}).get('bear',{})
    ok = (b.get('command')=='bearcli' and b.get('args')==['mcp-server'])
    print('OK' if ok else 'FAIL')
except: print('NOCFG')
"
}

mcp_configure() {
  python3 - "$1" <<'PYEOF'
import sys, json
mcp_file = sys.argv[1]
try:
    with open(mcp_file) as f: config = json.load(f)
except: config = {}

existing = config.get("mcpServers", {}).get("bear", {})
correct = {"command": "bearcli", "args": ["mcp-server"]}
if existing == correct:
    print("OK")
else:
    status = "UPD" if existing else "NEW"
    config.setdefault("mcpServers", {})["bear"] = correct
    with open(mcp_file, "w") as f: json.dump(config, f, indent=2, ensure_ascii=False)
    print(status)
PYEOF
}

# ── Main logic ───────────────────────────────────────────────────
bearcli_ok="OK"
command -v bearcli &>/dev/null || bearcli_ok="MISS"

echo "=== bear-notes skill installer ==="
echo "Source: $SKILL_SRC"
echo ""

if $UNINSTALL; then
  echo "Removing bear-notes symlinks..."
  for entry in "${AGENTS[@]}"; do
    read -r name dtype dval sdir mcp <<< "$entry"
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
  read -r name dtype dval sdir mcp <<< "$entry"

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
    mcp_result=$(mcp_configure "$mcp")
  elif $CHECK_ONLY; then
    mcp_result=$(mcp_status "$mcp")
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

echo ""
echo -e "Summary: ${GREEN}$installed installed${NC}, $skipped skipped (not detected)"
echo -e "MCP:     $mcp_ok already configured, $mcp_new newly configured"
