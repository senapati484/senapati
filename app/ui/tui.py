import os
import sys
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    from textual.app import App, ComposeResult
    from textual.widgets import Static, Input, RichLog, Header, Footer
    from textual.reactive import reactive
    from textual import work
except ImportError:
    logger.warning("textual not available, TUI disabled")
    App = None


ORB_STATES = {
    "idle": {"shape": "●", "color": "magenta", "animation": "slow_pulse"},
    "listening": {"shape": "◎", "color": "cyan", "animation": "expanding"},
    "thinking": {"shape": "◐", "color": "yellow", "animation": "rotating"},
    "speaking": {"shape": "◉", "color": "green", "animation": "waveform"},
    "error": {"shape": "✕", "color": "red", "animation": "flicker"},
    "muted": {"shape": "○", "color": "white", "animation": "static"},
}


class OrbWidget(Static):
    """Animated orb widget."""
    
    state = reactive("idle")
    frame = reactive(0)
    
    def render(self) -> str:
        state_config = ORB_STATES.get(self.state, ORB_STATES["idle"])
        return f"[{state_config['color']}]{state_config['shape']}[/]"
    
    def watch_state(self, state: str) -> None:
        self.refresh()


class SenapatiTUI(App if App else object):
    """Terminal UI for Senapati."""
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2;
        grid-rows: 1fr 4fr;
    }
    
    #sidebar {
        width: 100%;
        height: 100%;
        background: $surface;
    }
    
    #main {
        width: 100%;
        height: 100%;
    }
    
    #orb_container {
        height: 3;
        content-align: center middle;
    }
    
    #stats_container {
        width: 100%;
        height: 100%;
    }
    
    #conversation {
        width: 100%;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }
    
    #input_container {
        width: 100%;
        height: auto;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("b", "run_brief", "Brief"),
        ("m", "toggle_mute", "Mute"),
    ]
    
    def __init__(self, agent_ref=None):
        super().__init__()
        self.agent = agent_ref
        self.conversation_log: List[Dict[str, str]] = []
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        yield Static("✨ SENAPATI", id="title")
        yield OrbWidget(id="orb")
        yield Static(self._get_stats(), id="stats")
        yield RichLog(id="conversation")
        yield Input(placeholder="Type a message...", id="input")
        yield Footer()
    
    def _get_stats(self) -> str:
        """Get system stats for display."""
        try:
            import psutil
            
            cpu = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory()
            battery = psutil.sensors_battery()
            
            stats = f"CPU {cpu}% | RAM {ram.percent}%"
            
            if battery:
                stats += f" | 🔋 {battery.percent}%"
            
            return stats
        
        except:
            return "CPU -- | RAM --"
    
    def on_mount(self) -> None:
        """On mount."""
        self.set_interval(2, self._update_stats)
        self.title = "✨ Senapati"
    
    def _update_stats(self) -> None:
        """Update stats display."""
        try:
            stats_widget = self.query_one("#stats", Static)
            stats_widget.update(self._get_stats())
        except:
            pass
    
    def on_input_submit(self, event: Input.Submit) -> None:
        """Handle input submit."""
        user_input = event.value
        
        if not user_input:
            return
        
        self._add_message("user", user_input)
        
        if self.agent:
            response = self.agent.handle_input(user_input)
            self._add_message("assistant", response.get("speak", ""))
    
    def _add_message(self, role: str, content: str) -> None:
        """Add message to conversation."""
        timestamp = datetime.now().strftime("%H:%M")
        
        log = self.query_one("#conversation", RichLog)
        log.write(f"[{timestamp}] {role}: {content}")
        
        self.conversation_log.append({
            "role": role,
            "content": content,
        })
    
    def action_run_brief(self) -> None:
        """Run morning brief."""
        if self.agent:
            brief = self.agent.run_morning_brief()
            self._add_message("assistant", brief)
    
    def action_toggle_mute(self) -> None:
        """Toggle mute."""
        if self.agent:
            self.agent.toggle_mute()
            muted = self.agent.muted
            self._add_message("assistant", f"Muted: {muted}")


def run_tui(agent_ref=None) -> None:
    """Run the terminal UI."""
    if App is None:
        print("textual not installed. Install with: pip install textual")
        return
    
    app = SenapatiTUI(agent_ref)
    app.run()


def quick_status() -> str:
    """Get quick status for CLI."""
    stats = _get_stats()
    return f"✨ {stats}"