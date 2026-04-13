#!/usr/bin/env bash
# Senapati ✨ — One-Shot Installer
# Zero external dependencies. No brew. No apt. No sudo.
set -euo pipefail

SENAPATI_HOME="$HOME/.senapati"
SENAPATI_REPO="https://github.com/senapati484/senapati.git"
MODEL_MAIN="mlx-community/Qwen3-1.7B-4bit"
MODEL_DRAFT="mlx-community/Qwen3-0.6B-4bit"
PIPER_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US"
LAUNCHER="$HOME/.local/bin/senapati"
LAUNCH_AGENT="$HOME/Library/LaunchAgents/com.senapati.daemon.plist"

GRN='\033[0;32m'; YLW='\033[1;33m'; RED='\033[0;31m'; BLD='\033[1m'; RST='\033[0m'
ok()   { echo -e "${GRN}✓${RST} $1"; }
info() { echo -e "${YLW}→${RST} $1"; }
err()  { echo -e "${RED}✗${RST} $1"; exit 1; }
hdr()  { echo -e "\n${BLD}── $1 ──${RST}"; }

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
echo "  No brew. No apt. No sudo. Just Python 3.10+."
echo ""
read -rp "  Press Enter to install, or Ctrl+C to cancel... "

hdr "Step 1 — Detecting your system"
OS=$(uname -s)
ARCH=$(uname -m)
IS_MACOS=false
IS_APPLE_SILICON=false

if [ "$OS" = "Darwin" ]; then
  IS_MACOS=true
  [ "$ARCH" = "arm64" ] && IS_APPLE_SILICON=true
  ok "macOS detected (arch: $ARCH)"
elif [ "$OS" = "Linux" ]; then
  ok "Linux detected (arch: $ARCH)"
else
  err "Unsupported OS: $OS"
fi

command -v python3 >/dev/null 2>&1 || err "Python 3 not found. Install from https://python.org"
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_OK=$(python3 -c "import sys; print('yes' if sys.version_info >= (3,10) else 'no')")
[ "$PY_OK" = "yes" ] || err "Python 3.10+ required. You have $PY_VER"
ok "Python $PY_VER found"
command -v curl >/dev/null 2>&1 || err "curl not found"
ok "curl found"
command -v git >/dev/null 2>&1 || err "git not found"
ok "git found"

hdr "Step 2 — Creating ~/.senapati/ structure"
mkdir -p "$SENAPATI_HOME/models/piper" "$SENAPATI_HOME/memory" \
         "$SENAPATI_HOME/plugins" "$SENAPATI_HOME/logs" \
         "$SENAPATI_HOME/cache/screenshots" "$SENAPATI_HOME/venv" \
         "$SENAPATI_HOME/app" "$SENAPATI_HOME/training"
ok "Folder structure created at $SENAPATI_HOME"

hdr "Step 3 — Creating isolated Python environment"
python3 -m venv "$SENAPATI_HOME/venv"
source "$SENAPATI_HOME/venv/bin/activate"
pip install --upgrade pip setuptools wheel -q 2>&1 | grep -v "^WARNING" || true
ok "Virtual environment ready at $SENAPATI_HOME/venv"

hdr "Step 4 — Installing Python packages"
info "Installing LLM runtime..."
if [ "$IS_APPLE_SILICON" = "true" ]; then
  pip install mlx-lm -q
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

info "Installing OCR..."
if [ "$IS_MACOS" = "true" ]; then
  pip install ocrmac pyobjc-framework-Vision pyobjc-framework-Cocoa -q
  ok "ocrmac installed (Apple Vision — no brew needed)"
else
  pip install easyocr -q
  ok "easyocr installed"
fi

info "Installing notifications..."
if [ "$IS_MACOS" = "true" ]; then
  pip install macos-notifications -q
  ok "macos-notifications installed"
else
  pip install notify-py -q
  ok "notify-py installed"
fi

info "Installing memory engine..."
pip install sqlite-vec -q
ok "sqlite-vec installed"

info "Installing terminal UI (Textual)..."
pip install textual -q
ok "textual installed"

info "Installing MCP (FastMCP)..."
pip install fastmcp -q
ok "fastmcp installed"

info "Installing system utilities..."
pip install psutil watchdog Pillow huggingface_hub \
    sentence-transformers python-telegram-bot \
    PyGithub spotipy vobject rumps -q
ok "All system utilities installed"

if [ "$IS_MACOS" = "false" ]; then
  pip install sounddevice soundfile -q
  ok "Audio libs installed (Linux)"
fi

hdr "Step 5 — Downloading AI models (~1.5GB total)"
info "Models go to $SENAPATI_HOME/models/ — only happens once"

info "Downloading Qwen3-1.7B main model..."
python3 -c "
from huggingface_hub import snapshot_download
import os
snapshot_download(repo_id='$MODEL_MAIN',
  local_dir=os.path.expanduser('~/.senapati/models/qwen3-1.7b-mlx'),
  ignore_patterns=['*.md','*.txt'])
print('OK')
"
ok "Main model downloaded"

info "Downloading Qwen3-0.6B draft model..."
python3 -c "
from huggingface_hub import snapshot_download
import os
snapshot_download(repo_id='$MODEL_DRAFT',
  local_dir=os.path.expanduser('~/.senapati/models/qwen3-0.6b-mlx'),
  ignore_patterns=['*.md','*.txt'])
print('OK')
"
ok "Draft model downloaded"

info "Installing embedding model (all-MiniLM-L6-v2)..."
python3 -c "
from sentence_transformers import SentenceTransformer
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
print('OK')
" 2>&1 | grep -v "^Warning\|UNEXPECTED\|Notes:\|Key \|---\|LOAD REPORT\|embeddings.position"
ok "Embedding model ready"
ok "All AI models downloaded"

hdr "Step 6 — Downloading Piper voice models"
curl -L --progress-bar -o "$SENAPATI_HOME/models/piper/en_US-lessac-high.onnx" \
  "$PIPER_BASE/lessac/high/en_US-lessac-high.onnx"
curl -L -s -o "$SENAPATI_HOME/models/piper/en_US-lessac-high.onnx.json" \
  "$PIPER_BASE/lessac/high/en_US-lessac-high.onnx.json"
ok "Lessac voice downloaded"

info "Downloading Joe voice..."
curl -L --progress-bar -o "$SENAPATI_HOME/models/piper/en_US-joe-medium.onnx" \
  "$PIPER_BASE/joe/medium/en_US-joe-medium.onnx"
curl -L -s -o "$SENAPATI_HOME/models/piper/en_US-joe-medium.onnx.json" \
  "$PIPER_BASE/joe/medium/en_US-joe-medium.onnx.json"
ok "Joe voice downloaded"

hdr "Step 7 — Setting up wake word models"
python3 -c "
import openwakeword
import shutil
import os

# Download models to package directory
openwakeword.utils.download_models()

# Copy ONNX models to ~/.senapati/models/
pkg_models = os.path.join(os.path.dirname(openwakeword.__file__), 'resources', 'models')
dest_dir = os.path.expanduser('~/.senapati/models')
os.makedirs(dest_dir, exist_ok=True)

for f in os.listdir(pkg_models):
    src = os.path.join(pkg_models, f)
    dst = os.path.join(dest_dir, f)
    if os.path.isfile(src):
        shutil.copy2(src, dst)
        print(f'Copied: {f}')

print('OK')
"
ok "Wake word models ready"

hdr "Step 8 — Cloning Senapati source"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -d "$SENAPATI_HOME/app/.git" ]; then
  info "Already cloned — pulling latest..."
  git -C "$SENAPATI_HOME/app" pull --quiet
  ok "App updated"
elif [ -d "$SCRIPT_DIR/.git" ] && [ -d "$SCRIPT_DIR/app" ]; then
  cp -r "$SCRIPT_DIR/app/." "$SENAPATI_HOME/app/"
  ok "Copied local app source"
else
  info "Cloning from GitHub..."
  git clone "$SENAPATI_REPO" "$SENAPATI_HOME/app" --depth 1 -q
  ok "Cloned from GitHub"
fi
if [ -f "$SENAPATI_HOME/app/requirements.txt" ]; then
  cp "$SENAPATI_HOME/app/requirements.txt" "$SENAPATI_HOME/requirements.txt"
fi

hdr "Step 9 — Initializing memory database"
python3 -c "
import sqlite3, os
db = os.path.expanduser('~/.senapati/memory/senapati.db')
c = sqlite3.connect(db)
c.executescript('''
CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, started_at DATETIME, summary TEXT, tags TEXT);
CREATE TABLE IF NOT EXISTS turns (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT, timestamp DATETIME, FOREIGN KEY (session_id) REFERENCES sessions(id));
CREATE VIRTUAL TABLE IF NOT EXISTS turns_fts USING fts5(content, content=turns);
CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, content TEXT, confidence REAL, created_at DATETIME, last_seen DATETIME);
CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, description TEXT, due_at DATETIME, done INTEGER DEFAULT 0, created_at DATETIME);
CREATE TABLE IF NOT EXISTS habits (id INTEGER PRIMARY KEY AUTOINCREMENT, tool TEXT NOT NULL, args_json TEXT NOT NULL, weekday TEXT NOT NULL, hour INTEGER NOT NULL, count INTEGER DEFAULT 1, last_seen TEXT NOT NULL);
''')
c.commit()
c.close()
print('DB ready')
"
ok "Database ready"

hdr "Step 10 — Writing configuration"
python3 -c "
import json, os
cfg = {
  'name': 'Senapati',
  'user_name': None,
  'wake_words': ['hey senapati', 'hey buddy', 'senapati'],
  'wake_sensitivity': 0.72,
  'model': {
    'main': 'qwen3-1.7b-mlx',
    'draft': 'qwen3-0.6b-mlx',
    'embed': 'sentence-transformers/all-MiniLM-L6-v2',
    'runtime': 'mlx',
    'max_tokens': 300,
    'temperature': 0.1
  },
  'voice': {
    'stt_model': 'small',
    'tts_voice': 'en_US-joe-medium',
    'tts_speed': 0.95,
    'tts_sentence_silence': 0.2,
    'silence_timeout_ms': 1200
  },
  'memory': {
    'session_summary_after_days': 14,
    'max_context_turns': 8,
    'watch_dirs': ['~/Documents', '~/Desktop', '~/Developer']
  },
  'safety': {
    'trusted_mode': False,
    'require_approval_for_shell': True,
    'require_approval_for_delete': True,
    'require_approval_for_messages': True
  },
  'plugins': {
    'telegram': {'enabled': False, 'bot_token': None},
    'github': {'enabled': False, 'token': None},
    'spotify': {'enabled': False}
  },
  'brief': {
    'enabled': True, 'time': '08:00',
    'read_calendar': True, 'read_git_status': True, 'read_notifications': True
  },
  'ui': {'default_mode': 'daemon', 'show_hud': True},
  'onboarded': False
}
with open(os.path.expanduser('~/.senapati/config.json'), 'w') as f:
    json.dump(cfg, f, indent=2)
print('Config written')
"
ok "Config written"

hdr "Step 11 — Registering senapati command"
mkdir -p "$HOME/.local/bin"
python3 -c "
import os, stat
launcher = os.path.expanduser('~/.local/bin/senapati')
home = os.path.expanduser('~/.senapati')
lines = [
  '#!/usr/bin/env bash\n',
  'source \"' + home + '/venv/bin/activate\"\n',
  'export SENAPATI_HOME=\"' + home + '\"\n',
  'python3 \"' + home + '/app/main.py\" \"\$@\"\n',
]
with open(launcher, 'w') as f:
    f.writelines(lines)
os.chmod(launcher, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
print('Launcher written')
"
for rc in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.profile"; do
  if [ -f "$rc" ] && ! grep -q ".local/bin" "$rc" 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
  fi
done
ok "senapati command registered at $LAUNCHER"

hdr "Step 12 — macOS auto-start on login"
if [ "$IS_MACOS" = "true" ]; then
  mkdir -p "$HOME/Library/LaunchAgents"
  python3 -c "
import os
launcher = os.path.expanduser('~/.local/bin/senapati')
home = os.path.expanduser('~/.senapati')
plist_path = os.path.expanduser('~/Library/LaunchAgents/com.senapati.daemon.plist')
content = (
  '<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n'
  '<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\"\n'
  '  \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n'
  '<plist version=\"1.0\">\n<dict>\n'
  '  <key>Label</key>\n  <string>com.senapati.daemon</string>\n'
  '  <key>ProgramArguments</key>\n  <array>\n'
  '    <string>' + launcher + '</string>\n'
  '    <string>--daemon</string>\n'
  '  </array>\n'
  '  <key>RunAtLoad</key>\n  <true/>\n'
  '  <key>KeepAlive</key>\n  <true/>\n'
  '  <key>ThrottleInterval</key>\n  <integer>10</integer>\n'
  '  <key>StandardOutPath</key>\n  <string>' + home + '/logs/daemon.log</string>\n'
  '  <key>StandardErrorPath</key>\n  <string>' + home + '/logs/errors.log</string>\n'
  '  <key>EnvironmentVariables</key>\n  <dict>\n'
  '    <key>PATH</key>\n'
  '    <string>' + os.path.expanduser('~/.local/bin') + ':/usr/local/bin:/usr/bin:/bin</string>\n'
  '    <key>SENAPATI_HOME</key>\n    <string>' + home + '</string>\n'
  '  </dict>\n</dict>\n</plist>\n'
)
with open(plist_path, 'w') as f:
    f.write(content)
print('LaunchAgent written')
"
  launchctl load "$LAUNCH_AGENT" 2>/dev/null || true
  ok "LaunchAgent installed — Senapati starts on every login"

  hdr "Step 12b — macOS Permissions"
  echo ""
  echo "  Senapati needs 3 permissions in System Settings."
  echo "  System Settings will open — find your terminal app and toggle ON."
  echo ""
  echo "  ┌─────────────────────────────────────────────────────┐"
  echo "  │  Terminal app name: Terminal / iTerm2 / Warp        │"
  echo "  │                                                     │"
  echo "  │  1. Microphone       → toggle your terminal ON      │"
  echo "  │  2. Accessibility    → toggle your terminal ON      │"
  echo "  │  3. Screen Recording → toggle your terminal ON      │"
  echo "  │                                                     │"
  echo "  │  Not listed? Click + → /Applications/Utilities/    │"
  echo "  │  Terminal.app → Open → toggle ON                    │"
  echo "  └─────────────────────────────────────────────────────┘"
  echo ""
  read -rp "  Press Enter to open System Settings..."
  open "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone" 2>/dev/null || true
  sleep 2
  open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility" 2>/dev/null || true
  sleep 2
  open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture" 2>/dev/null || true
  echo ""
  read -rp "  Press Enter once all 3 are granted... "
  ok "Permissions acknowledged"
fi

hdr "Step 13 — Personalisation"
echo ""
read -rp "  What should Senapati call you? (Enter to skip): " USER_NAME
if [ -n "$USER_NAME" ]; then
  python3 -c "
import json, os, sys
name = sys.argv[1]
path = os.path.expanduser('~/.senapati/config.json')
with open(path) as f:
    cfg = json.load(f)
cfg['user_name'] = name
cfg['onboarded'] = True
with open(path, 'w') as f:
    json.dump(cfg, f, indent=2)
print('Saved: ' + name)
" "$USER_NAME"
  ok "Name saved: $USER_NAME"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          ✨  Senapati is installed and running!          ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Commands:                                               ║"
echo "║    senapati              → launch with terminal UI       ║"
echo "║    senapati --daemon     → background voice agent        ║"
echo "║    senapati --brief      → morning briefing              ║"
echo "║    senapati --update     → update from GitHub            ║"
echo "║  Wake words:  'Hey Senapati'  or  'Hey Buddy'            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

export PATH="$HOME/.local/bin:$PATH"
info "Starting Senapati daemon..."
senapati --daemon &
sleep 1
ok "Done. Say 'Hey Senapati' to wake it up."