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
                self.agent_state = agent_state_ref
                # Don't call super().__init__ here - defer until run()
                # to avoid NSWindow/AppKit main thread violations
                self._deferred_init = True
                self.timer = None

            def run(self):
                # Proper initialization on main thread with event loop running
                super().__init__("⭐", title="⭐", quit_button=None)

                # Build menu items after super().__init__ so AppKit is ready
                self.menu = [
                    rumps.MenuItem("● Idle"),
                    None,
                    rumps.MenuItem("Open Terminal UI", callback=self.launch_terminal),
                    rumps.MenuItem("Morning Brief", callback=self.run_brief),
                    None,
                    rumps.MenuItem("Mute Wake Word", callback=self.toggle_mute),
                    rumps.MenuItem("Trusted Mode: Off", callback=self.toggle_trusted),
                    None,
                    rumps.MenuItem("Quit Senapati", callback=self.quit_senapati),
                ]

                self.timer = rumps.Timer(self.update_status, 2)
                self.timer.start()

                # Now run the actual AppKit event loop
                rumps.App.run(self)

            def update_status(self, _):
                state = self.agent_state.get("state", "idle")

                status_labels = {
                    "idle":      "● Idle",
                    "listening": "◎ Listening...",
                    "thinking":  "◐ Thinking...",
                    "speaking":  "◉ Speaking...",
                    "error":     "✕ Error",
                    "muted":     "○ Muted",
                }
                bar_icons = {
                    "idle":      "⭐",
                    "listening": "🎤",
                    "thinking":  "💭",
                    "speaking":  "🔊",
                    "muted":     "🔇",
                    "error":     "⚠️",
                }

                # Update the title bar icon
                self.title = bar_icons.get(state, "⭐")

                # Update status label
                try:
                    self.menu["● Idle"] = status_labels.get(state, "● Idle")
                except (KeyError, AttributeError):
                    pass

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
                sender.title = "Unmute Wake Word" if muted else "Mute Wake Word"

            def toggle_trusted(self, sender):
                trusted = self.agent_state.get("trusted_mode", False)
                self.agent_state["trusted_mode"] = not trusted
                sender.title = f"Trusted Mode: {'On' if self.agent_state['trusted_mode'] else 'Off'}"

            def quit_senapati(self, _):
                try:
                    import rumps
                    rumps.notification("Senapati", "", "Shutting down.")
                except:
                    pass
                rumps.quit_application()

        app = SenapatiMenuBar(agent_state_ref)
        app.run()  # This calls our overridden run() which does proper init

    except ImportError:
        logger.error("rumps not installed")
    except Exception as e:
        logger.error(f"Menu bar error: {e}")
        import traceback
        traceback.print_exc()


def start_menubar(agent_state: Dict[str, Any]) -> None:
    """Start menu bar in background thread."""
    thread = threading.Thread(
        target=run_menubar,
        args=(agent_state,),
        daemon=True,
    )
    thread.start()
    logger.info("Menu bar started")