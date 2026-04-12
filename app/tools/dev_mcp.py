import os
import subprocess
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


def git_status(repo_path: str = ".") -> str:
    """Get git status of a repository."""
    try:
        repo_path = os.path.expanduser(repo_path)
        
        result = subprocess.run(
            ["git", "-C", repo_path, "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            return f"Not a git repo: {repo_path}"
        
        status = result.stdout.strip()
        
        if not status:
            return "Clean working tree."
        
        lines = status.split("\n")
        output = []
        
        for line in lines[:20]:
            if line:
                status_code = line[:2]
                file_path = line[3:]
                
                if "M" in status_code:
                    output.append(f"  Modified: {file_path}")
                elif "A" in status_code:
                    output.append(f"  Added: {file_path}")
                elif "D" in status_code:
                    output.append(f"  Deleted: {file_path}")
                elif "?" in status_code:
                    output.append(f"  Untracked: {file_path}")
                else:
                    output.append(f"  {line}")
        
        return "\n".join(output) if output else "No changes."
    
    except Exception as e:
        return f"Error: {e}"


def git_log(repo_path: str = ".", n: int = 10) -> str:
    """Get last N commits."""
    try:
        repo_path = os.path.expanduser(repo_path)
        
        result = subprocess.run(
            [
                "git", "-C", repo_path, "log",
                f"-{n}",
                "--oneline",
                "--format=%h %s (%an, %ar)"
            ],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            return f"Not a git repo: {repo_path}"
        
        commits = result.stdout.strip()
        
        if not commits:
            return "No commits yet."
        
        lines = commits.split("\n")
        output = []
        
        for i, line in enumerate(lines, 1):
            output.append(f"{i}. {line}")
        
        return "\n".join(output)
    
    except Exception as e:
        return f"Error: {e}"


def git_diff(repo_path: str = ".", file: str = "") -> str:
    """Get git diff."""
    try:
        repo_path = os.path.expanduser(repo_path)
        
        args = ["git", "-C", repo_path, "diff"]
        
        if file:
            args.append("--")
            args.append(file)
        
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            return f"Error: {result.stderr}"
        
        diff = result.stdout.strip()
        
        if not diff:
            return "No changes."
        
        return diff[:3000]
    
    except Exception as e:
        return f"Error: {e}"


def git_branch(repo_path: str = ".") -> str:
    """Get current branch."""
    try:
        repo_path = os.path.expanduser(repo_path)
        
        result = subprocess.run(
            ["git", "-C", repo_path, "branch", "--show-current"],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            return f"Not a git repo: {repo_path}"
        
        return result.stdout.strip() or "detached"
    
    except Exception as e:
        return f"Error: {e}"


def run_dev_server(
    project_path: str,
    command: str = "npm run dev",
    port: Optional[int] = None,
) -> str:
    """Start a dev server in the background."""
    try:
        project_path = os.path.expanduser(project_path)
        
        if not os.path.exists(project_path):
            return f"Project not found: {project_path}"
        
        env = os.environ.copy()
        env["FOREGROUND"] = "1"
        
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=project_path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        return f"Started dev server (PID: {process.pid})"
    
    except Exception as e:
        return f"Error: {e}"


def stop_dev_server(port: int) -> str:
    """Stop dev server on port."""
    try:
        if os.system == "Darwin":
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
            )
            
            pids = result.stdout.strip().split("\n")
            
            for pid in pids:
                if pid:
                    subprocess.run(["kill", pid])
            
            return f"Stopped processes on port {port}"
        else:
            return f"Port {port} stopped"
    
    except Exception as e:
        return f"Error: {e}"


def open_in_editor(path: str) -> str:
    """Open file in default editor."""
    try:
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            return f"File not found: {path}"
        
        if os.system == "Darwin":
            subprocess.run(["open", "-a", "Visual Studio Code", path])
        else:
            subprocess.run(["code", path])
        
        return f"Opened {path}"
    
    except Exception as e:
        return f"Error: {e}"


def open_in_browser(url: str) -> str:
    """Open URL in default browser."""
    try:
        if os.system == "Darwin":
            subprocess.run(["open", url])
        else:
            subprocess.run(["xdg-open", url])
        
        return f"Opened {url}"
    
    except Exception as e:
        return f"Error: {e}"


def get_package_json(project_path: str = ".") -> Dict[str, Any]:
    """Get package.json info."""
    try:
        import json
        
        project_path = os.path.expanduser(project_path)
        pkg_path = os.path.join(project_path, "package.json")
        
        if not os.path.exists(pkg_path):
            return {"error": "No package.json found"}
        
        with open(pkg_path) as f:
            pkg = json.load(f)
        
        return {
            "name": pkg.get("name", "unknown"),
            "version": pkg.get("version", "unknown"),
            "scripts": list(pkg.get("scripts", {}).keys()),
            "dependencies": len(pkg.get("dependencies", {})),
            "dev_dependencies": len(pkg.get("devDependencies", {})),
        }
    
    except Exception as e:
        return {"error": str(e)}


def check_dependencies(project_path: str = ".") -> str:
    """Check for outdated dependencies."""
    try:
        project_path = os.path.expanduser(project_path)
        
        result = subprocess.run(
            ["npm", "outdated"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            return "No outdated dependencies."
        
        return result.stdout.strip()[:1000]
    
    except Exception as e:
        return f"Error: {e}"


def explain_code(
    user_question: str,
    code_text: str,
    file_path: str = "",
    language: str = "",
) -> str:
    """Explain code using LLM - PROMPT_18."""
    from app.core import brain
    from app.prompts import build_code_explain_prompt, parse_json_response
    
    prompt = build_code_explain_prompt(
        user_question=user_question,
        code_text=code_text[:3000],
        file_path=file_path,
        language=language,
    )
    
    try:
        response = brain.generate(prompt, max_tokens=128)
        data = parse_json_response(response)
        return data.get("speak", "Couldn't explain that.")
    except Exception as e:
        return f"Error: {e}"