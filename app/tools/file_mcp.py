import os
import subprocess
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


def search_files(query: str, directory: str = "~") -> List[str]:
    """Search files by name or content."""
    try:
        directory = os.path.expanduser(directory)
        
        if not os.path.exists(directory):
            return [f"Directory not found: {directory}"]
        
        result = subprocess.run(
            ["find", directory, "-name", f"*{query}*", "-type", "f"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        files = [f for f in result.stdout.strip().split("\n") if f][:20]
        return files if files else ["No files found."]
    
    except Exception as e:
        return [f"Error: {e}"]


def read_file(path: str) -> str:
    """Read and return file contents."""
    try:
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            return f"File not found: {path}"
        
        if not os.path.isfile(path):
            return f"Not a file: {path}"
        
        size = os.path.getsize(path)
        if size > 100000:
            return f"File too large: {size} bytes. Use summarize instead."
        
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        return content[:5000]
    
    except Exception as e:
        return f"Error: {e}"


def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    try:
        path = os.path.expanduser(path)
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return f"Written to {path}"
    
    except Exception as e:
        return f"Error: {e}"


def move_file(src: str, dst: str) -> str:
    """Move or rename a file."""
    try:
        src = os.path.expanduser(src)
        dst = os.path.expanduser(dst)
        
        if not os.path.exists(src):
            return f"Source not found: {src}"
        
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        
        os.rename(src, dst)
        return f"Moved to {dst}"
    
    except Exception as e:
        return f"Error: {e}"


def copy_file(src: str, dst: str) -> str:
    """Copy a file."""
    try:
        import shutil
        
        src = os.path.expanduser(src)
        dst = os.path.expanduser(dst)
        
        if not os.path.exists(src):
            return f"Source not found: {src}"
        
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        
        return f"Copied to {dst}"
    
    except Exception as e:
        return f"Error: {e}"


def delete_file(path: str) -> str:
    """Delete a file."""
    try:
        import shutil
        
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            return f"Not found: {path}"
        
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        
        return f"Deleted {path}"
    
    except Exception as e:
        return f"Error: {e}"


def summarize_folder(path: str) -> str:
    """List and summarize folder contents."""
    try:
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            return f"Folder not found: {path}"
        
        if not os.path.isdir(path):
            return f"Not a folder: {path}"
        
        entries = os.listdir(path)
        
        if not entries:
            return "Empty folder."
        
        files = []
        dirs = []
        
        for entry in entries[:20]:
            full_path = os.path.join(path, entry)
            if os.path.isdir(full_path):
                count = len(os.listdir(full_path))
                dirs.append(f"{entry}/ ({count} items)")
            else:
                size = os.path.getsize(full_path)
                size_str = _format_size(size)
                files.append(f"{entry} ({size_str})")
        
        parts = []
        if dirs:
            parts.append("Folders:\n  " + "\n  ".join(dirs[:10]))
        if files:
            parts.append("Files:\n  " + "\n  ".join(files[:10]))
        
        return "\n\n".join(parts)
    
    except Exception as e:
        return f"Error: {e}"


def _format_size(size: int) -> str:
    """Format file size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size}{unit}"
        size //= 1024
    return f"{size}TB"


def get_file_info(path: str) -> Dict[str, Any]:
    """Get file information."""
    try:
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            return {"error": "File not found"}
        
        stat = os.stat(path)
        
        return {
            "path": path,
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "is_dir": os.path.isdir(path),
            "is_file": os.path.isfile(path),
        }
    
    except Exception as e:
        return {"error": str(e)}


def list_directory(path: str = "~") -> str:
    """List directory contents."""
    return summarize_folder(path)