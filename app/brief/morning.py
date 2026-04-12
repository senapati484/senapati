import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def generate_brief(
    user_name: str = "there",
    date_string: Optional[str] = None,
) -> str:
    """Generate morning briefing."""
    if not date_string:
        now = datetime.now()
        date_string = now.strftime("%A, %B %d")
    
    parts = []
    
    parts.append(f"Good morning. It's {date_string}.")
    
    events = _get_calendar_events()
    if events:
        parts.append(_format_calendar_events(events))
    
    git_status = _get_git_status()
    if git_status:
        parts.append(git_status)
    
    notifications = _get_notification_summary()
    if notifications:
        parts.append(notifications)
    
    battery = _get_battery()
    if battery is not None and battery < 30:
        parts.append(f"Battery is at {battery}%. Time to charge up.")
    
    tasks = _get_pending_tasks()
    if tasks:
        parts.append(f"You have {len(tasks)} pending task{'s' if len(tasks) > 1 else ''}.")
    
    parts.append("What would you like to work on today?")
    
    return " ".join(parts)


def _get_calendar_events() -> list:
    """Get today's calendar events."""
    try:
        if os.system == "Darwin":
            return _get_calendar_events_mac()
        else:
            return _get_calendar_events_linux()
    
    except Exception as e:
        logger.error(f"Calendar error: {e}")
        return []


def _get_calendar_events_mac() -> list:
    """Get calendar events on macOS."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["icalbuddy", "-b", "", "-e", "1", "today"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        if result.returncode != 0:
            return []
        
        events = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                events.append(line.strip())
        
        return events[:5]
    
    except:
        return []


def _get_calendar_events_linux() -> list:
    """Get calendar events on Linux."""
    return []


def _format_calendar_events(events: list) -> str:
    """Format calendar events for speaking."""
    if not events:
        return ""
    
    if len(events) == 1:
        return f"You have 1 event today: {events[0]}."
    
    return f"You have {len(events)} events today: {events[0]} and {events[1]}."


def _get_git_status() -> str:
    """Get git status summary."""
    try:
        import os
        import subprocess
        
        dev_dir = os.path.expanduser("~/Developer")
        
        if not os.path.exists(dev_dir):
            return ""
        
        repos = []
        
        for item in os.listdir(dev_dir):
            path = os.path.join(dev_dir, item)
            git_dir = os.path.join(path, ".git")
            
            if os.path.isdir(path) and os.path.exists(git_dir):
                repos.append(item)
        
        if not repos:
            return ""
        
        uncommitted = []
        
        for repo in repos[:3]:
            path = os.path.join(dev_dir, repo)
            
            try:
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                
                if result.stdout.strip():
                    uncommitted.append(repo)
            
            except:
                pass
        
        if uncommitted:
            return f"You have uncommitted changes in {len(uncommitted)} repo{'s' if len(uncommitted) > 1 else ''}: {', '.join(uncommitted)}."
        
        return ""
    
    except Exception as e:
        logger.error(f"Git status error: {e}")
        return ""


def _get_notification_summary() -> str:
    """Get notification summary."""
    try:
        import subprocess
        
        if os.system != "Darwin":
            return ""
        
        result = subprocess.run(
            ["osascript", "-e", 'tell app "System Events" to get description of (processes whose background only is false)'],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            return ""
        
        apps = result.stdout.strip().split(", ")
        
        priority_apps = ["Slack", "Messages", "Mail", "Telegram"]
        
        for app in apps:
            for priority in priority_apps:
                if priority.lower() in app.lower():
                    return f"You have unread notifications in {app}."
        
        return ""
    
    except:
        return ""


def _get_battery() -> Optional[int]:
    """Get battery percentage."""
    try:
        import psutil
        
        battery = psutil.sensors_battery()
        
        if battery:
            return battery.percent
    
    except:
        pass
    
    return None


def _get_pending_tasks() -> list:
    """Get pending tasks."""
    try:
        from app.memory import store
        
        tasks = store.get_tasks(done=False)
        
        return [t["description"] for t in tasks[:3]]
    
    except:
        return []


def generate_eod_brief(
    user_name: str = "there",
) -> str:
    """Generate end-of-day briefing."""
    from datetime import datetime
    
    now = datetime.now()
    date_string = now.strftime("%A, %B %d")
    
    parts = []
    
    parts.append(f"Good evening. It's {date_string}.")
    
    tasks_done = _get_completed_tasks_today()
    tasks_pending = _get_pending_tasks()
    
    if tasks_done:
        parts.append(f"You completed {len(tasks_done)} task{'s' if len(tasks_done) > 1 else ''} today.")
    
    if tasks_pending:
        parts.append(f"{len(tasks_pending)} task{'s' if len(tasks_pending) > 1 else ''} pending for tomorrow.")
    
    if not tasks_done and not tasks_pending:
        parts.append("Quiet day — or a good rest day, depending how you look at it.")
    
    parts.append("See you tomorrow!")
    
    return " ".join(parts)


def _get_completed_tasks_today() -> list:
    """Get tasks completed today."""
    try:
        from app.memory import store
        
        tasks = store.get_tasks(done=True)
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        completed = []
        for task in tasks:
            created = task.get("created_at", "")[:10]
            if created == today:
                completed.append(task["description"])
        
        return completed
    
    except:
        return []