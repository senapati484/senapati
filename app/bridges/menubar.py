import os
import logging
import subprocess
import threading
import platform
from typing import Dict, Any

logger = logging.getLogger(__name__)

SENAPATI_HOME = os.path.expanduser("~/.senapati")


def run_menubar(agent_state_ref: Dict[str, Any]) -> None:
    """Run menu bar app."""
    if platform.system() != "Darwin":
        logger.warning("Menu bar only on macOS")
        return
    
    try:
        import rumps
        
        class SenapatiMenuBar(rumps.App):
            def __init__(self, agent_state_ref):
                super().__init__("✨", title="✨")
                self.agent_state = agent_state_ref
                
                self.status_item = rumps.MenuItem("● Starting...")
                self.open_terminal = rumps.MenuItem("Open Terminal", callback=self.launch_terminal)
                self.morning_brief = rumps.MenuItem("Morning Brief", callback=self.run_brief)
                self.mute_toggle = rumps.MenuItem("Mute Wake Word", callback=self.toggle_mute)
                self.trusted_toggle = rumps.MenuItem("Trusted Mode: Off", callback=self.toggle_trusted)
                self.quit_button = rumps.MenuItem("Quit", callback=self.quit_senapati)
                
                self.app.menu = [
                    self.status_item, None,
                    self.open_terminal, self.morning_brief, None,
                    self.mute_toggle, self.trusted_toggle, None,
                    self.quit_button,
                ]
                
                self.timer = rumps.Timer(self.update_status, 2)
                self.timer.start()
            
            def update_status(self, _):
                state = self.agent_state.get("state", "idle")
                
                icons = {
                    "idle": "● Idle",
                    "listening": "◎ Listening...",
                    "thinking": "◐ Thinking...",
                    "speaking": "◉ Speaking...",
                    "error": "✕ Error",
                    "muted": "○ Muted",
                }
                
                self.status_item.title = icons.get(state, "● Running")
                
                state_icons = {
                    "idle": "✨",
                    "listening": "🎤",
                    "thinking": "💭",
                    "speaking": "🔊",
                }
                
                self.title = state_icons.get(state, "✨")
            
            def launch_terminal(self, _):
                if platform.system() == "Darwin":
                    script = 'tell app "Terminal" to do script "senapati"'
                    subprocess.Popen(
                        ["osascript", "-e", script],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
            
            def run_brief(self, _):
                subprocess.Popen(
                    [
                        f"{SENAPATI_HOME}/venv/bin/python",
                        f"{SENAPATI_HOME}/app/main.py",
                        "--brief",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            
            def toggle_mute(self, sender):
                muted = self.agent_state.get("muted", False)
                self.agent_state["muted"] = not muted
                sender.title = "Unmute Wake Word" if not muted else "Mute Wake Word"
            
            def toggle_trusted(self, sender):
                trusted = self.agent_state.get("trusted_mode", False)
                self.agent_state["trusted_mode"] = not trusted
                sender.title = f"Trusted Mode: {'On' if not trusted else 'Off'}"
            
            def quit_senapati(self, _):
                try:
                    import rumps
                    rumps.notification("Senapati", "", "Shutting down.")
                except:
                    pass
                rumps.quit_application()
        
        app = SenapatiMenuBar(agent_state_ref)
        app.run()
    
    except ImportError:
        logger.error("rumps not installed")
    except Exception as e:
        logger.error(f"Menu bar error: {e}")


def start_menubar(agent_state: Dict[str, Any]) -> None:
    """Start menu bar in background thread."""
    thread = threading.Thread(
        target=run_menubar,
        args=(agent_state,),
        daemon=True,
    )
    thread.start()
    logger.info("Menu bar started")