#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════╗
# ║           SENAPATI ✨ — One-Shot Installer               ║
# ║   Zero external dependencies. No brew. No apt. No pip    ║
# ║   outside this script. Just: curl ... | bash             ║
# ╚══════════════════════════════════════════════════════════╝
set -euo pipefail

# ── Constants ────────────────────────────────────────────────
SENAPATI_HOME="$HOME/.senapati"
SENAPATI_REPO="https://github.com/senapati484/senapati"
MODEL_MAIN="mlx-community/Qwen3-1.7B-4bit"
MODEL_DRAFT="mlx-community/Qwen3-0.6B-4bit"
MODEL_EMBED="mlx-community/nomic-embed-text-v1.5"
PIPER_VOICE_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high"
PIPER_VOICE_FILE="en_US-lessac-high"
LAUNCH_AGENT="$HOME/Library/LaunchAgents/com.senapati.daemon.plist"

# ── Colors ───────────────────────────────────────────────────
GRN='\033[0;32m'; YLW='\033[1;33m'; RED='\033[0;31m'; BLD='\033[1m'; RST='\033[0m'
ok()   { echo -e "${GRN}✓${RST} $1"; }
info() { echo -e "${YLW}→${RST} $1"; }
err()  { echo -e "${RED}✗${RST} $1"; exit 1; }
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

        Your local AI friend. Always running. Zero cloud.
        Wake words: "Hey Senapati"  |  "Hey Buddy"

BANNER
echo "  This installer requires nothing except Python 3.10+."
echo "  No brew. No apt. No sudo. Just pip inside a venv."
echo ""
read -p "  Press Enter to install, or Ctrl+C to cancel..."

# ═══════════════════════════════════════════════════════════
# STEP 1 — System detection
# ═══════════════════════════════════════════════════════════
hdr "Step 1 — Detecting your system"

OS=$(uname -s)
ARCH=$(uname -m)
IS_APPLE_SILICON=false
IS_MACOS=false
IS_LINUX=false

case "$OS" in
  Darwin)
    IS_MACOS=true
    [[ "$ARCH" == "arm64" ]] && IS_APPLE_SILICON=true
    ok "macOS detected (arch: $ARCH)"
    ;;
  Linux)
    IS_LINUX=true
    ok "Linux detected (arch: $ARCH)"
    ;;
  *)
    err "Unsupported OS: $OS. Senapati supports macOS and Linux."
    ;;
esac

# Python check — must be 3.10+, no external install needed
if ! command -v python3 &>/dev/null; then
  err "Python 3 not found. Install from https://python.org and re-run."
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [[ "$PY_MAJOR" -lt 3 ]] || [[ "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 10 ]]; then
  err "Python 3.10+ required. You have $PY_VERSION. Install from https://python.org"
fi
ok "Python $PY_VERSION found"

# curl check — should always be present
command -v curl &>/dev/null || err "curl not found. Install it for your OS."
ok "curl found"

# git check
command -v git &>/dev/null || err "git not found. Install from https://git-scm.com"
ok "git found"

# ═══════════════════════════════════════════════════════════
# STEP 2 — Create folder structure
# ═══════════════════════════════════════════════════════════
hdr "Step 2 — Creating ~/.senapati/ structure"

mkdir -p "$SENAPATI_HOME"/{models/piper,memory,plugins,logs,cache/screenshots,venv,app,training}
ok "Folder structure created at $SENAPATI_HOME"

# ═══════════════════════════════════════════════════════════
# STEP 3 — Python virtual environment
# ═══════════════════════════════════════════════════════════
hdr "Step 3 — Creating isolated Python environment"

python3 -m venv "$SENAPATI_HOME/venv"
source "$SENAPATI_HOME/venv/bin/activate"
pip install --upgrade pip setuptools wheel -q
ok "Virtual environment ready at $SENAPATI_HOME/venv"

# ═══════════════════════════════════════════════════════════
# STEP 4 — Install ALL Python dependencies (no system tools)
# ═══════════════════════════════════════════════════════════
hdr "Step 4 — Installing Python packages (this takes ~3 min)"

# ── Core AI + voice stack ─────────────────────────────────
info "Installing LLM runtime..."
if [[ "$IS_APPLE_SILICON" == "true" ]]; then
  pip install mlx-lm -q            # Native Apple Silicon GPU runtime
else
  pip install llama-cpp-python -q
fi
ok "LLM runtime installed"

info "Installing speech-to-text (faster-whisper)..."
pip install faster-whisper -q
ok "faster-whisper installed"

info "Installing wake word engine (openWakeWord)..."
pip install openwakeword -q
ok "openWakeWord installed"

info "Installing text-to-speech (piper-tts)..."
pip install piper-tts -q
ok "piper-tts installed"

# ── OCR — NO tesseract, NO brew ──────────────────────────
info "Installing OCR..."
if [[ "$IS_MACOS" == "true" ]]; then
  pip install ocrmac pyobjc-framework-Vision pyobjc-framework-Cocoa -q
  ok "ocrmac installed (uses Apple Vision — better than tesseract, no brew)"
else
  pip install easyocr -q
  ok "easyocr installed"
fi

# ── Notifications ────────────────────────────────────────
info "Installing notifications..."
if [[ "$IS_MACOS" == "true" ]]; then
  pip install macos-notifications -q
  ok "macos-notifications installed"
else
  pip install notify-py -q
  ok "notify_py installed"
fi

# ── Memory + vector store ────────────────────────────────
info "Installing memory engine..."
pip install sqlite-vec -q
ok "sqlite-vec installed"

# ── Terminal UI ──────────────────────────────────────────
info "Installing terminal UI (Textual)..."
pip install textual -q
ok "textual installed"

# ── MCP tool protocol ────────────────────────────────────
info "Installing MCP (FastMCP)..."
pip install fastmcp -q
ok "fastmcp installed"

# ── System utilities ─────────────────────────────────────
info "Installing system utilities..."
pip install \
  psutil \
  watchdog \
  Pillow \
  pytesseract \
  huggingface_hub \
  python-telegram-bot \
  PyGithub \
  spotipy \
  vobject \
  sounddevice \
  soundfile \
  rumps \
  -q
ok "All system utilities installed"

# ═══════════════════════════════════════════════════════════
# STEP 5 — Download LLM models from HuggingFace
# ═══════════════════════════════════════════════════════════
hdr "Step 5 — Downloading AI models (this is the big download ~3GB)"
info "Models go to $SENAPATI_HOME/models/ — only happens once"
echo ""

info "Downloading Qwen3-1.7B main model..."
python3 - << 'PYEOF'
from huggingface_hub import snapshot_download
import os
snapshot_download(
    repo_id="mlx-community/Qwen3-1.7B-4bit",
    local_dir=os.path.expanduser("~/.senapati/models/qwen3-1.7b-mlx"),
    ignore_patterns=["*.md", "*.txt"]
)
print("✓ Main model downloaded")
PYEOF

info "Downloading Qwen3-0.6B draft model..."
python3 - << 'PYEOF'
from huggingface_hub import snapshot_download
import os
snapshot_download(
    repo_id="mlx-community/Qwen3-0.6B-4bit",
    local_dir=os.path.expanduser("~/.senapati/models/qwen3-0.6b-mlx"),
    ignore_patterns=["*.md", "*.txt"]
)
print("✓ Draft model downloaded")
PYEOF

info "Installing embedding model (all-MiniLM-L6-v2)..."
pip install sentence-transformers -q
python3 - << 'PYEOF'
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
print("✓ Embedding model ready")
PYEOF

ok "All AI models downloaded"

# ═══════════════════════════════════════════════════════════
# STEP 6 — Download Piper voice model
# ═══════════════════════════════════════════════════════════
hdr "Step 6 — Downloading Piper voice (en_US-lessac-high)"

curl -L --progress-bar \
  -o "$SENAPATI_HOME/models/piper/${PIPER_VOICE_FILE}.onnx" \
  "${PIPER_VOICE_BASE}/${PIPER_VOICE_FILE}.onnx"

curl -L -s \
  -o "$SENAPATI_HOME/models/piper/${PIPER_VOICE_FILE}.onnx.json" \
  "${PIPER_VOICE_BASE}/${PIPER_VOICE_FILE}.onnx.json"

ok "Voice model downloaded"

  # Also download Joe voice (deeper, more dominant)
  info "Downloading Joe voice (dominant + warm)..."
  curl -L --progress-bar \
  -o "$SENAPATI_HOME/models/piper/en_US-joe-medium.onnx" \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/joe/medium/en_US-joe-medium.onnx"

  curl -L -s \
  -o "$SENAPATI_HOME/models/piper/en_US-joe-medium.onnx.json" \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/joe/medium/en_US-joe-medium.onnx.json"

  ok "Joe voice downloaded"

# ═══════════════════════════════════════════════════════════
# STEP 7 — Download openWakeWord models
# ═══════════════════════════════════════════════════════════
hdr "Step 7 — Setting up wake word models"

python3 - << 'PYEOF'
import openwakeword
openwakeword.utils.download_models()
print("✓ openWakeWord base models downloaded")
PYEOF

ok "Wake word models ready"

# ═══════════════════════════════════════════════════════════
# STEP 8 — Clone Senapati app source
# ═══════════════════════════════════════════════════════════
hdr "Step 8 — Cloning Senapati source"

if [ -d "$SENAPATI_HOME/app/.git" ]; then
  info "App already cloned — pulling latest..."
  git -C "$SENAPATI_HOME/app" pull --quiet
else
  # Clone from current directory if it's a git repo, otherwise from GitHub
  CURRENT_DIR="$(cd "$(dirname "$0")" && pwd)"
  if [ -d "$CURRENT_DIR/.git" ]; then
    cp -r "$CURRENT_DIR/app" "$SENAPATI_HOME/"
    ok "Copied local app source"
  else
    git clone "$SENAPATI_REPO" "$SENAPATI_HOME/app" --depth 1 -q
    ok "Cloned from GitHub"
  fi
fi

# ═══════════════════════════════════════════════════════════
# STEP 9 — Initialize SQLite database
# ═══════════════════════════════════════════════════════════
hdr "Step 9 — Initializing memory database"

python3 << 'PYEOF'
import sqlite3, os

db_path = os.path.expanduser("~/.senapati/memory/senapati.db")
conn = sqlite3.connect(db_path)
conn.executescript("""
  CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    started_at DATETIME,
    summary TEXT,
    tags TEXT
  );
  CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    role TEXT,
    content TEXT,
    timestamp DATETIME,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
  );
  CREATE VIRTUAL TABLE IF NOT EXISTS turns_fts USING fts5(content, content=turns);
  CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    content TEXT,
    confidence REAL,
    created_at DATETIME,
    last_seen DATETIME
  );
  CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT,
    due_at DATETIME,
    done INTEGER DEFAULT 0,
    created_at DATETIME
  );
  CREATE TABLE IF NOT EXISTS habits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool TEXT NOT NULL,
    args_json TEXT NOT NULL,
    weekday TEXT NOT NULL,
    hour INTEGER NOT NULL,
    count INTEGER DEFAULT 1,
    last_seen TEXT NOT NULL
  );
""")
conn.commit()
conn.close()
print("✓ Memory database initialized")
PYEOF

ok "Database ready"

# ═══════════════════════════════════════════════════════════
# STEP 10 — Write config.json
# ═══════════════════════════════════════════════════════════
hdr "Step 10 — Writing configuration"

cat > "$SENAPATI_HOME/config.json" << 'CONFJSON'
{
  "name": "Senapati",
  "user_name": null,
  "wake_words": ["hey senapati", "hey buddy", "senapati"],
  "wake_sensitivity": 0.72,
  "model": {
    "main": "qwen3-1.7b-mlx",
    "draft": "qwen3-0.6b-mlx",
    "embed": "sentence-transformers/all-MiniLM-L6-v2",
    "runtime": "mlx",
    "max_tokens": 300,
    "temperature": 0.1
  },
  "voice": {
    "stt_model": "small",
    "tts_voice": "en_US-joe-medium",
    "tts_speed": 0.95,
    "tts_sentence_silence": 0.2,
    "silence_timeout_ms": 1200,
    "audio_backend": "afplay"
  },
  "memory": {
    "session_summary_after_days": 14,
    "max_context_turns": 8,
    "watch_dirs": ["~/Documents", "~/Desktop", "~/Developer"]
  },
  "safety": {
    "trusted_mode": false,
    "require_approval_for_shell": true,
    "require_approval_for_delete": true,
    "require_approval_for_messages": true
  },
  "plugins": {
    "telegram": { "enabled": false, "bot_token": null },
    "github": { "enabled": false, "token": null },
    "spotify": { "enabled": false }
  },
  "brief": {
    "enabled": true,
    "time": "08:00",
    "read_calendar": true,
    "read_git_status": true,
    "read_notifications": true
  },
  "ui": {
    "default_mode": "daemon",
    "show_hud": true
  },
  "onboarded": false
}
CONFJSON

ok "Config written"

# ═══════════════════════════════════════════════════════════
# STEP 11 — Register CLI command
# ═══════════════════════════════════════════════════════════
hdr "Step 11 — Registering senapati command"

mkdir -p "$HOME/.local/bin"
LAUNCHER="$HOME/.local/bin/senapati"

cat > "$LAUNCHER" << LAUNCHSCRIPT
#!/usr/bin/env bash
source "$SENAPATI_HOME/venv/bin/activate"
export SENAPATI_HOME="$SENAPATI_HOME"
python3 "$SENAPATI_HOME/app/main.py" "\$@"
LAUNCHSCRIPT

chmod +x "$LAUNCHER"

# Add to PATH if not already present
add_to_path() {
  local shell_rc="$1"
  if [ -f "$shell_rc" ] && ! grep -q ".local/bin" "$shell_rc"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$shell_rc"
  fi
}
add_to_path "$HOME/.zshrc"
add_to_path "$HOME/.bashrc"
add_to_path "$HOME/.profile"

ok "senapati command registered at $LAUNCHER"

# ═══════════════════════════════════════════════════════════
# STEP 12 — macOS LaunchAgent for auto-start (macOS only)
# ═══════════════════════════════════════════════════════════
if [[ "$IS_MACOS" == "true" ]]; then
  hdr "Step 12 — Setting up auto-start on login (LaunchAgent)"
  mkdir -p "$HOME/Library/LaunchAgents"

  cat > "$LAUNCH_AGENT" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.senapati.daemon</string>
  <key>ProgramArguments</key>
  <array>
    <string>$LAUNCHER</string>
    <string>--daemon</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>ThrottleInterval</key>
  <integer>10</integer>
  <key>StandardOutPath</key>
  <string>$SENAPATI_HOME/logs/daemon.log</string>
  <key>StandardErrorPath</key>
  <string>$SENAPATI_HOME/logs/errors.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>SENAPATI_HOME</key>
    <string>$SENAPATI_HOME</string>
  </dict>
</dict>
</plist>
PLIST

  launchctl load "$LAUNCH_AGENT" 2>/dev/null || true
  ok "LaunchAgent installed — Senapati starts on login automatically"

  # ── macOS permissions wizard ─────────────────────────────
  hdr "Step 12b — macOS Permissions"
  echo ""
  echo "  Senapati needs 4 permissions in System Settings > Privacy & Security."
  echo "  We'll open each panel — grant access to Terminal."
  echo ""
  echo "  ┌──────────────────────────────────────────────────────┐"
  echo "  │  1. Microphone          (to hear your voice)         │"
  echo "  │  2. Accessibility       (to control apps)            │"
  echo "  │  3. Screen Recording    (for screen-read / OCR)      │"
  echo "  │  4. Notifications       (to read system alerts)      │"
  echo "  └──────────────────────────────────────────────────────┘"
  echo ""
  read -p "  Press Enter to open System Settings for each permission..."

  open "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
  sleep 1
  open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
  sleep 1
  open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
  sleep 1
  open "x-apple.systempreferences:com.apple.preference.security?Privacy_Notifications"

  echo ""
  echo "  Grant access in each panel, then come back here."
  read -p "  Press Enter when all 4 permissions are granted..."
  ok "Permissions acknowledged"
fi

# ═══════════════════════════════════════════════════════════
# STEP 13 — Ask for user's name (personalisation)
# ═══════════════════════════════════════════════════════════
hdr "Step 13 — Quick personalisation"

echo ""
read -p "  What should Senapati call you? (press Enter to skip): " USER_NAME

if [[ -n "$USER_NAME" ]]; then
  python3 - "$USER_NAME" << 'PYEOF'
import sys, json, os
name = sys.argv[1]
path = os.path.expanduser("~/.senapati/config.json")
with open(path) as f:
    cfg = json.load(f)
cfg["user_name"] = name
cfg["onboarded"] = True
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
print(f"✓ Name saved")
PYEOF
  ok "Name saved: $USER_NAME"
fi

# ═══════════════════════════════════════════════════════════
# DONE
# ═══════════════════════════════════════════════════════════
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          ✨  Senapati is installed and running!          ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                          ║"
echo "║   Commands:                                              ║"
echo "║     senapati              → launch with terminal UI      ║"
echo "║     senapati --daemon     → background mode (running)    ║"
echo "║     senapati --brief      → morning briefing now         ║"
echo "║     senapati --mini       → minimal HUD                  ║"
echo "║     senapati --update     → update to latest version     ║"
echo "║                                                          ║"
echo "║   Wake words:                                            ║"
echo "║     'Hey Senapati'  or  'Hey Buddy'                      ║"
echo "║                                                          ║"
echo "║   First launch:  senapati  (runs onboarding flow)        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Reload PATH and start
export PATH="$HOME/.local/bin:$PATH"
info "Starting Senapati daemon now..."
senapati --daemon &
echo ""
ok "Senapati is listening. Say 'Hey Senapati' to wake it up."