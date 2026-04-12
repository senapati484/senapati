import os
import logging
import threading
from typing import List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

WATCH_DIRS = [
    os.path.expanduser("~/Documents"),
    os.path.expanduser("~/Desktop"),
    os.path.expanduser("~/Developer"),
]

SUPPORTED_EXTENSIONS = [".md", ".txt", ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml"]

_indexed_docs = {}


def start_indexing() -> None:
    """Start indexing documents in background."""
    observer = Observer()
    
    for directory in WATCH_DIRS:
        if os.path.exists(directory):
            handler = DocumentIndexHandler()
            observer.schedule(handler, directory, recursive=True)
            logger.info(f"Watching {directory}")
    
    observer.start()
    logger.index("Document indexing started")


def stop_indexing() -> None:
    """Stop indexing."""
    observer.stop()
    observer.join()
    logger.index("Document indexing stopped")


class DocumentIndexHandler(FileSystemEventHandler):
    """Handle file system events for indexing."""
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        path = event.src_path
        
        if not _should_index(path):
            return
        
        index_file(path)
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        path = event.src_path
        
        if not _should_index(path):
            return
        
        index_file(path)


def _should_index(path: str) -> bool:
    """Check if file should be indexed."""
    for ext in SUPPORTED_EXTENSIONS:
        if path.endswith(ext):
            return True
    
    return False


def index_file(path: str) -> None:
    """Index a file."""
    try:
        if not os.path.exists(path):
            return
        
        if os.path.getsize(path) > 1000000:
            logger.debug(f"Skipping large file: {path}")
            return
        
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        _indexed_docs[path] = {
            "content": content[:10000],
            "modified": os.path.getmtime(path),
        }
        
        logger.debug(f"Indexed: {path}")
    
    except Exception as e:
        logger.error(f"Index error: {e}")


def search_index(query: str) -> List[str]:
    """Search indexed documents."""
    results = []
    
    query_lower = query.lower()
    
    for path, doc in _indexed_docs.items():
        content = doc.get("content", "").lower()
        
        if query_lower in content:
            results.append(path)
    
    return results[:10]


def get_index_stats() -> dict:
    """Get indexing statistics."""
    return {
        "indexed_count": len(_indexed_docs),
        "watch_dirs": len(WATCH_DIRS),
    }


def clear_index() -> None:
    """Clear the index."""
    global _indexed_docs
    _indexed_docs = {}
    logger.info("Index cleared")


def remove_from_index(path: str) -> None:
    """Remove file from index."""
    if path in _indexed_docs:
        del _indexed_docs[path]
        logger.debug(f"Removed from index: {path}")