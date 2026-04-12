import os
import logging
import queue
import threading
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)

notif_queue = queue.Queue()
_watch_thread = None
_stop_event = threading.Event()


PRIORITY_APPS = ["Messages", "Mail", "Slack", "Telegram", "Calendar", "GitHub"]


def start_watching(on_notification: Optional[Callable] = None) -> None:
    """Start watching notifications."""
    global _watch_thread, _stop_event
    
    if _watch_thread is not None:
        return
    
    _stop_event.clear()
    _watch_thread = threading.Thread(
        target=_watch_loop,
        args=(on_notification,),
        daemon=True,
    )
    _watch_thread.start()
    logger.info("Notification watching started")


def _watch_loop(on_notification: Optional[Callable]) -> None:
    """Watch for notifications."""
    import platform
    
    if platform.system() != "Darwin":
        return
    
    try:
        import objc
        from Foundation import NSDistributedNotificationCenter, NSRunLoop
        
        center = NSDistributedNotificationCenter.defaultCenter()
        
        class NotifObserver(objc.lookUpClass("NSObject")):
            def handleNotification_(self, notif):
                try:
                    info = notif.userInfo() or {}
                    app = str(info.get("NSDistributedNotificationSender", "Unknown"))
                    title = str(info.get("NSDistributedNotificationTitle", ""))
                    body = str(info.get("NSDistributedNotificationBody", ""))
                    
                    notif_data = {
                        "app": app,
                        "title": title,
                        "body": body,
                    }
                    
                    notif_queue.put(notif_data)
                    
                    if on_notification:
                        on_notification(notif_data)
                
                except Exception as e:
                    logger.error(f"Notification handler error: {e}")
        
        observer = NotifObserver.alloc().init()
        center.addObserver_selector_name_object_(
            observer, "handleNotification:", None, None
        )
        
        NSRunLoop.currentRunLoop().run()
    
    except Exception as e:
        logger.error(f"Notification watch failed: {e}")


def stop_watching() -> None:
    """Stop watching notifications."""
    global _watch_thread, _stop_event
    
    _stop_event.set()
    if _watch_thread:
        _watch_thread.join(timeout=2)
        _watch_thread = None
    
    logger.info("Notification watching stopped")


def get_notification() -> Optional[Dict[str, Any]]:
    """Get next notification from queue."""
    try:
        return notif_queue.get_nowait()
    except queue.Empty:
        return None


def get_pending_notifications() -> list:
    """Get all pending notifications."""
    notifs = []
    
    while True:
        try:
            notif = notif_queue.get_nowait()
            notifs.append(notif)
        except queue.Empty:
            break
    
    return notifs


def send_notification(title: str, message: str) -> str:
    """Send a notification."""
    import platform
    
    try:
        if platform.system() == "Darwin":
            from mac_notifications import client
            client.create_notification(
                title=title,
                subtitle=message,
                sound="Ping",
            )
            return "Notification sent."
        else:
            from notifypy import Notify
            
            n = Notify()
            n.title = title
            n.message = message
            n.send()
            return "Notification sent."
    
    except ImportError:
        return _send_notification_fallback(title, message)
    except Exception as e:
        return f"Error: {e}"


def _send_notification_fallback(title: str, message: str) -> str:
    """Fallback notification on macOS."""
    import platform
    import subprocess
    
    if platform.system() == "Darwin":
        try:
            subprocess.run(
                ["osascript", "-e", f'display notification "{message}" with title "{title}"'],
                capture_output=True,
            )
            return "Notification sent."
        except:
            pass
    
    return "Notification not available"


def triage_notification(notif: Dict[str, Any]) -> str:
    """Triage notification - decide what to do."""
    from app.prompts import build_notification_triage_prompt
    
    from app.core import brain
    
    prompt = build_notification_triage_prompt(
        app=notif.get("app", "Unknown"),
        title=notif.get("title", ""),
        body=notif.get("body", ""),
        time="now",
        agent_state="idle",
        user_activity="unknown",
    )
    
    response = brain.generate(prompt, max_tokens=32)
    
    response = response.strip().lower()
    
    if "speak_now" in response:
        return "speak_now"
    elif "queue" in response:
        return "queue"
    else:
        return "log_only"


def is_priority_app(app: str) -> bool:
    """Check if notification is from priority app."""
    for priority in PRIORITY_APPS:
        if priority.lower() in app.lower():
            return True
    return False


def format_notification(notif: Dict[str, Any]) -> str:
    """Format notification for speaking."""
    app = notif.get("app", "Unknown")
    title = notif.get("title", "")
    body = notif.get("body", "")
    
    if body:
        return f"{app}: {title}. {body}"
    else:
        return f"{app}: {title}"