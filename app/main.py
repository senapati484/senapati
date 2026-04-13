#!/usr/bin/env python3
"""
Senapati ✨ — Main entry point
Handles: --daemon, --brief, --mini, --debug, --update flags
"""

import sys
import os
import argparse
import logging
import json
import platform
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────────────────
# main.py is at ~/.senapati/app/main.py
# Add ~/.senapati to path so "from app.core import ..." works
SCRIPT_DIR = Path(__file__).parent.resolve()
SENAPATI_APP_DIR = SCRIPT_DIR.parent  # ~/.senapati/
sys.path.insert(0, str(SENAPATI_APP_DIR))

SENAPATI_HOME = Path(os.environ.get("SENAPATI_HOME", Path.home() / ".senapati"))

# ── Logging setup ────────────────────────────────────────────────────────────
log_file = SENAPATI_HOME / "logs" / "senapati.log"
log_file.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("senapati")


def load_config() -> dict:
    config_path = SENAPATI_HOME / "config.json"
    if not config_path.exists():
        log.error(f"config.json not found at {config_path}")
        sys.exit(1)
    with open(config_path) as f:
        return json.load(f)


def check_models(config: dict) -> bool:
    """Verify required model files exist before starting."""
    models_dir = SENAPATI_HOME / "models"
    main_model = config["model"]["main"]
    main_path = models_dir / main_model

    if not main_path.exists():
        log.error(f"Main model not found at {main_path}")
        log.error("Run install.sh again or download models manually.")
        return False
    return True


def _is_already_running() -> bool:
    """Check if a Senapati instance is already running using a PID file."""
    lock_file = SENAPATI_HOME / ".senapati.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)

    # Check if lock file exists and if that PID is still running
    if lock_file.exists():
        try:
            pid_str = lock_file.read_text().strip()
            if pid_str:
                pid = int(pid_str)
                # Check if process is running using os.kill with signal 0
                # This raises OSError if process doesn't exist or we don't have permission
                import signal
                os.kill(pid, 0)
                # Process exists - check if it's actually a senapati process
                try:
                    proc_path = f"/proc/{pid}" if os.path.exists("/proc") else None
                    if proc_path:
                        with open(f"{proc_path}/cmdline", "r") as f:
                            cmdline = f.read()
                            if "senapati" in cmdline or "main.py" in cmdline:
                                log.warning(f"Another Senapati instance is running (PID: {pid})")
                                return True
                    else:
                        # On macOS, use ps to check
                        import subprocess
                        result = subprocess.run(
                            ["ps", "-p", str(pid), "-o", "command="],
                            capture_output=True, text=True
                        )
                        if "senapati" in result.stdout or "main.py" in result.stdout:
                            log.warning(f"Another Senapati instance is running (PID: {pid})")
                            return True
                except (PermissionError, ProcessLookupError):
                    pass
        except (ValueError, ProcessLookupError, PermissionError, OSError):
            # Stale lock file - process died or we don't have permission
            pass

    # Write our PID
    lock_file.write_text(str(os.getpid()))
    return False


def run_daemon(config: dict):
    """Background daemon — wake word always listening.

    On macOS, rumps MUST run on the main thread (AppKit requirement).
    All other work runs in background daemon threads.
    """
    import threading
    log.info("Starting Senapati daemon...")

    IS_MACOS = platform.system() == "Darwin"

    # Single shared state object for agent <-> menubar communication
    from core.agent import _shared_state
    _shared_state["state"] = "starting"
    _shared_state["muted"] = False
    _shared_state["trusted_mode"] = False

    # ── Start all background workers in threads ──────────────────────────────

    # Start document indexer in background
    try:
        from bridges.doc_indexer import start_indexer
        idx_thread = threading.Thread(target=start_indexer, daemon=True, name="indexer")
        idx_thread.start()
        log.info("Document indexer started")
    except ImportError as e:
        log.warning(f"Indexer unavailable: {e}")

    # Start notification bridge on macOS
    if IS_MACOS:
        try:
            from bridges.notif_bridge import start_notification_watcher
            notif_thread = threading.Thread(
                target=start_notification_watcher,
                daemon=True,
                name="notif_bridge"
            )
            notif_thread.start()
            log.info("Notification bridge started")
        except ImportError as e:
            log.warning(f"Notification bridge unavailable: {e}")

    # Start the main agent loop in a background thread
    def _run_agent():
        try:
            from core.agent import Agent
            agent = Agent(str(SENAPATI_HOME / "config.json"), shared_state=_shared_state)
            agent.start()
        except ImportError as e:
            log.error(f"Agent core not found: {e}")
            _run_minimal_daemon(config)

    agent_thread = threading.Thread(target=_run_agent, daemon=True, name="agent")
    agent_thread.start()
    log.info("Agent started in background thread")

    # ── Menu bar MUST run on main thread (AppKit / rumps requirement) ─────────
    if IS_MACOS:
        try:
            from bridges.menubar import run_menubar
            log.info("Menu bar starting on main thread...")
            run_menubar(_shared_state)   # blocks; runs the NSApplication event loop
        except ImportError as e:
            log.warning(f"Menu bar unavailable: {e}")
            agent_thread.join()        # keep process alive without menu bar
    else:
        agent_thread.join()            # Linux: just wait for agent


def _run_minimal_daemon(config: dict):
    """Fallback minimal daemon."""
    import time
    log.info("Running minimal daemon (core agent not yet implemented)")
    log.info(f"User: {config.get('user_name', 'unknown')}")
    log.info(f"Model: {config['model']['main']}")
    log.info(f"Wake words: {config['wake_words']}")
    log.info("Daemon is running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(10)
            log.debug("Daemon heartbeat — all good")
    except KeyboardInterrupt:
        log.info("Daemon stopped.")


def run_brief(config: dict):
    """Morning briefing mode."""
    try:
        from brief.morning import generate_and_speak_brief
        generate_and_speak_brief(config, SENAPATI_HOME)
    except ImportError:
        import datetime
        now = datetime.datetime.now()
        msg = f"Good morning. It's {now.strftime('%A, %B %d')}. Senapati is ready."
        print(msg)
        try:
            from core.voice_out import speak
            speak(msg, SENAPATI_HOME, config)
        except ImportError:
            log.warning("TTS not available yet — brief printed to console only")


def run_tui(config: dict):
    """Launch the full Textual terminal UI."""
    try:
        from ui.tui import SenapatiApp
        app = SenapatiApp(config=config, home=SENAPATI_HOME)
        app.run()
    except ImportError as e:
        log.error(f"Terminal UI not available: {e}")
        log.info("Falling back to daemon mode")
        run_daemon(config)


def run_update():
    """Pull latest version from GitHub."""
    import subprocess
    app_dir = SENAPATI_HOME / "app"
    if (app_dir / ".git").exists():
        log.info("Updating Senapati from GitHub...")
        result = subprocess.run(
            ["git", "pull", "--rebase"],
            cwd=app_dir,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✓ Updated successfully")
            print(result.stdout)
        else:
            print("✗ Update failed")
            print(result.stderr)
    else:
        print("Not a git repo — re-run install.sh to update")


def main():
    parser = argparse.ArgumentParser(
        description="Senapati ✨ — Your local AI friend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  senapati             → full terminal UI
  senapati --daemon    → background voice agent
  senapati --brief     → morning briefing
  senapati --mini      → minimal status view
  senapati --update    → update from GitHub
  senapati --debug     → verbose logging

Wake words: "Hey Senapati" or "Hey Buddy"
        """
    )
    parser.add_argument("--daemon", action="store_true", help="Run as background daemon")
    parser.add_argument("--brief", action="store_true", help="Run morning briefing")
    parser.add_argument("--mini", action="store_true", help="Minimal HUD mode")
    parser.add_argument("--update", action="store_true", help="Update from GitHub")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        log.debug("Debug mode enabled")

    log.info("Starting Senapati...")

    # Single-instance check
    if _is_already_running():
        log.warning("Senapati is already running. Exiting.")
        print("Senapati is already running. Use 'senapati --daemon' to check status.")
        sys.exit(1)

    config = load_config()
    log.info(f"Loaded config — user: {config.get('user_name', 'unknown')}")

    if not check_models(config):
        log.warning("Models missing — continuing in limited mode")

    if args.update:
        run_update()
    elif args.brief:
        run_brief(config)
    elif args.daemon:
        log.info("Running daemon...")
        run_daemon(config)
    elif args.mini:
        log.info("Mini mode not yet implemented — running daemon")
        run_daemon(config)
    else:
        run_tui(config)


if __name__ == "__main__":
    main()