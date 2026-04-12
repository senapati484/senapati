import os
import subprocess
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def open_app(name: str) -> str:
    """Open a macOS application by name."""
    try:
        subprocess.run(
            ["open", "-a", name],
            check=True,
            capture_output=True,
        )
        return f"Opened {name}"
    except subprocess.CalledProcessError as e:
        return f"Failed to open {name}: {e}"
    except Exception as e:
        return f"Error: {e}"


def close_app(name: str) -> str:
    """Close a macOS application."""
    try:
        subprocess.run(
            ["osascript", "-e", f'tell app "{name}" to quit'],
            check=True,
            capture_output=True,
        )
        return f"Closed {name}"
    except Exception as e:
        return f"Error: {e}"


def get_system_stats() -> Dict[str, Any]:
    """Get CPU, RAM, and battery stats."""
    try:
        import psutil
        
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        
        stats = {
            "cpu_percent": cpu,
            "ram_used_gb": round(ram.used / 1e9, 2),
            "ram_percent": ram.percent,
        }
        
        battery = psutil.sensors_battery()
        if battery:
            stats["battery_percent"] = battery.percent
            stats["battery_charging"] = battery.is_plugged
        
        return stats
    
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        return {"error": str(e)}


def set_volume(level: int) -> str:
    """Set system volume 0-100."""
    try:
        if os.system == "Darwin":
            subprocess.run(
                ["osascript", "-e", f"set volume output volume {level}"],
                check=True,
                capture_output=True,
            )
        else:
            subprocess.run(
                ["amixer", "sset", "Master", f"{level}%"],
                check=True,
                capture_output=True,
            )
        return f"Volume set to {level}%"
    except Exception as e:
        return f"Error: {e}"


def run_shell(command: str, require_approval: bool = True) -> str:
    """Run a shell command."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode == 0:
            return result.stdout[:2000] if result.stdout else "Command completed."
        else:
            return f"Error: {result.stderr[:500]}" if result.stderr else "Command failed."
    
    except subprocess.TimeoutExpired:
        return "Error: Command timed out."
    except Exception as e:
        return f"Error: {e}"


def get_clipboard() -> str:
    """Get clipboard content."""
    try:
        if os.system == "Darwin":
            result = subprocess.run(
                ["pbpaste"],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        else:
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"


def set_clipboard(text: str) -> str:
    """Set clipboard content."""
    try:
        if os.system == "Darwin":
            subprocess.run(
                ["pbcase"],
                input=text,
                text=True,
                check=True,
            )
        else:
            subprocess.run(
                ["xclip", "-selection", "clipboard", "-i"],
                input=text,
                text=True,
                check=True,
            )
        return "Clipboard set."
    except Exception as e:
        return f"Error: {e}"


def get_uptime() -> str:
    """Get system uptime."""
    try:
        if os.system == "Darwin":
            result = subprocess.run(
                ["uptime"],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        else:
            result = subprocess.run(
                ["uptime"],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
    except Exception as e:
        return str(e)


def get_disk_usage(path: str = "/") -> Dict[str, Any]:
    """Get disk usage for path."""
    try:
        import psutil
        usage = psutil.disk_usage(path)
        return {
            "total_gb": round(usage.total / 1e9, 2),
            "used_gb": round(usage.used / 1e9, 2),
            "free_gb": round(usage.free / 1e9, 2),
            "percent": usage.percent,
        }
    except Exception as e:
        return {"error": str(e)}


def list_processes(limit: int = 10) -> list:
    """List top processes by CPU usage."""
    try:
        import psutil
        processes = []
        for p in psutil.process_iter(["name", "cpu_percent"]):
            try:
                processes.append({
                    "name": p.info["name"],
                    "cpu": p.info["cpu_percent"],
                })
            except:
                pass
        
        processes.sort(key=lambda x: x.get("cpu", 0), reverse=True)
        return processes[:limit]
    except Exception as e:
        return [{"error": str(e)}]


def kill_process(name: str) -> str:
    """Kill process by name."""
    try:
        import psutil
        killed = False
        for p in psutil.process_iter(["name", "pid"]):
            if p.info["name"] == name:
                p.kill()
                killed = True
        
        return f"Killed {name}" if killed else f"{name} not found"
    except Exception as e:
        return f"Error: {e}"