#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════╗
# ║        SENAPATI ✨ — Uninstaller                      ║
# ║   Completely removes Senapati from your system         ║
# ╚══════════════════════════════════════════════════════════╝
set -euo pipefail

# ── Constants ────────────────────────────────────────────────
SENAPATI_HOME="$HOME/.senapati"
LAUNCH_AGENT="$HOME/Library/LaunchAgents/com.senapati.daemon.plist"
LAUNCHER="$HOME/.local/bin/senapati"

# ── Colors ───────────────────────────────────────────────────
GRN='\033[0;32m'; YLW='\033[1;33m'; RED='\033[0;31m'; BLD='\033[1m'; RST='\033[0m'
ok()   { echo -e "${GRN}✓${RST} $1"; }
info() { echo -e "${YLW}→${RST} $1"; }
err()  { echo -e "${RED}✗${RST} $1"; }
hdr()  { echo -e "\n${BLD}── $1 ──${RST}"; }

# ── Banner ───────────────────────────────────────────────────
clear
cat << 'BANNER'

  ███████╗███████╗███╗   ██╗ █████╗ ██████╗  █████╗ ████████╗██╗
  ██╔════╝██╔════╝████╗  ██║██╔══██╗██╔══██╗██╔══██╗╚══██╔══╝██║
  ███████╗█████╗  ██╔██╗ ██║███████║██████╔╝███████║   ██║   ██║
  ╚════██║██╔══╝  ██║╚██╗██║██╔══██║██╔═══╝ ██╔══██║   ██║   ██║
  ███████║███████╗██║ ╚████║██║  ██║██║     ██║  ██║   ██║   ██║
  ╚══════╝╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝   ╚═╝   ╚═╝

        Uninstalling Senapati...
        This will NOT delete your conversations or learned facts
        unless you explicitly choose to do so.

BANNER

# ═══════════════════════════════════════════════════════════
# STEP 1 — Stop the daemon
# ═══════════════════════════════════════════════════════════════════
hdr "Step 1 — Stopping Senapati daemon"

if [[ -f "$LAUNCH_AGENT" ]]; then
  launchctl unload "$LAUNCH_AGENT" 2>/dev/null || true
  rm -f "$LAUNCH_AGENT"
  ok "LaunchAgent removed"
else
  info "No LaunchAgent found (wasn't set up)"
fi

# Kill any running senapati processes
pkill -f "senapati" 2>/dev/null || true
pkill -f "com.senapati.daemon" 2>/dev/null || true
ok "Processes stopped"

# ════════════════════════════════════════════════════════���══
# STEP 2 — Remove CLI command
# ═══════════════════════════════════════════════════════════
hdr "Step 2 — Removing CLI command"

rm -f "$LAUNCHER"
ok "CLI command removed"

# Remove PATH entry from shell configs
remove_path_entry() {
  local rc_file="$1"
  if [[ -f "$rc_file" ]]; then
    sed -i '' '/\.local\/bin/d' "$rc_file" 2>/dev/null || true
  fi
}

remove_path_entry "$HOME/.zshrc"
remove_path_entry "$HOME/.bashrc"
remove_path_entry "$HOME/.profile"
ok "Shell configs cleaned"

# ═══════════════════════════════════════════════════════════
# STEP 3 — Ask about data
# ═══════════════════════════════════════════════════
hdr "Step 3 — User data"

echo ""
echo "  What would you like to do with your data?"
echo ""
echo "  ┌──────────────────────────────────────────────────────┐"
echo "  │  KEEP   — Keep ~/.senapati (conversations, facts)  │"
echo "  │  WIPE   — Delete everything (irreversible!)      │"
echo "  │  ASK    Later — I'll ask again after a month     │"
echo "  └──────────────────────────────────────────────────────┘"
echo ""
read -p "  Choice (KEEP/wipe/ask)? [KEEP]: " DATAChoice
DATAChoice="${DATAChoice:-KEEP}"

case "${DATAChoice,,}" in
  wipe|delete)
    rm -rf "$SENAPATI_HOME"
    ok "All user data deleted"
    ;;
  ask)
    # Create a reminder file for later
    mkdir -p "$SENAPATI_HOME"
    echo "uninstall_reminder" > "$SENAPATI_HOME/.uninstall_pending"
    info "We'll ask again in 30 days"
    ;;
  *)
    ok "Keeping ~/.senapati (your memories are safe)"
    ;;
esac

# ═══════════════════════════════════════════════════════════
# DONE
# ═══════════════════════════════════════════════════════════
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          ✨  Senapati has been uninstalled          ║"
echo "╠════════════════════════════════════════════════════════╣"
echo "║                                                          ║"
echo "   To reinstall:                                           ║"
echo "     curl -fsSL https://.../install.sh | bash              ║"
echo "                                                          ║"
echo "   Your conversations are preserved at ~/.senapati/            ║"
echo "   Reinstall to pick up where you left off                 ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""