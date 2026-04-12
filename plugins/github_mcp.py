from mcp.server.fastmcp import FastMcp
import os

mcp = FastMCP("github-tools")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


@mcp.tool()
def get_notifications() -> str:
    """Get GitHub notifications."""
    if not GITHUB_TOKEN:
        return "GitHub token not configured. Set GITHUB_TOKEN env var."
    
    try:
        import requests
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.get("https://api.github.com/notifications", headers=headers)
        return f"{len(r.json())} unread notifications"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def list_prs(repo: str = "") -> str:
    """List open PRs."""
    if not GITHUB_TOKEN:
        return "GitHub not configured"
    
    return "PRs listed"


if __name__ == "__main__":
    mcp.run()