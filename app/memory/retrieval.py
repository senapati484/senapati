import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

SENAPATI_HOME = os.path.expanduser("~/.senapati")


def retrieve_context(
    query: str = "",
    limit: int = 5,
) -> str:
    """
    Retrieve relevant context for current session.
    Returns formatted context string.
    """
    from app.memory import store
    
    context_parts = []
    
    facts = store.get_facts()
    if facts:
        context_parts.append("Facts:")
        for fact in facts[:limit]:
            content = fact.get("content", "")
            category = fact.get("category", "")
            context_parts.append(f"  • [{category}] {content}")
    
    tasks = store.get_tasks(done=False)
    if tasks:
        context_parts.append("Pending tasks:")
        for task in tasks[:limit]:
            desc = task.get("description", "")
            context_parts.append(f"  • {desc}")
    
    if not context_parts:
        return "No relevant context found."
    
    return "\n".join(context_parts)


def search_memory(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search memory for query.
    Returns list of matching entries.
    """
    from app.memory import store
    
    results = []
    
    turns = store.search_turns(query, limit)
    results.extend([
        {"type": "turn", "content": t["content"], "role": t["role"]}
        for t in turns
    ])
    
    facts = store.get_facts()
    for fact in facts:
        if query.lower() in fact.get("content", "").lower():
            results.append({
                "type": "fact",
                "content": fact["content"],
                "category": fact["category"],
            })
    
    return results[:limit]


def get_user_facts_summary() -> str:
    """Get summary of user facts."""
    from app.memory import store
    
    facts = store.get_facts()
    
    if not facts:
        return "(no facts known)"
    
    by_category = {}
    for fact in facts:
        cat = fact.get("category", "other")
        by_category.setdefault(cat, []).append(fact.get("content", ""))
    
    parts = []
    for cat, contents in by_category.items():
        if contents:
            parts.append(f"{cat}: {', '.join(contents[:2])}")
    
    return "; ".join(parts[:3])


def get_pending_tasks_summary() -> str:
    """Get summary of pending tasks."""
    from app.memory import store
    
    tasks = store.get_tasks(done=False)
    
    if not tasks:
        return "(no pending tasks)"
    
    return "; ".join([t["description"] for t in tasks[:3]])


def format_session_history(turns: List[Dict[str, str]]) -> str:
    """Format session history for injection."""
    if not turns:
        return "(no prior turns)"
    
    lines = []
    for turn in turns:
        role = turn.get("role", "?")
        content = turn.get("content", "")[:100]
        lines.append(f"{role}: {content}")
    
    return "\n".join(lines)


def retrieve_entity(
    entity_type: str,
    name: str,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve specific entity from memory.
    """
    from app.memory import store
    
    facts = store.get_facts(category=entity_type)
    
    for fact in facts:
        if name.lower() in fact.get("content", "").lower():
            return fact
    
    return None


def get_last_mentioned_file() -> Optional[str]:
    """Get the last mentioned file from session."""
    from app.memory import store
    
    sessions = store.get_recent_sessions(limit=1)
    
    if not sessions:
        return None
    
    session_id = sessions[0]["id"]
    turns = store.get_session_turns(session_id)
    
    for turn in reversed(turns):
        content = turn.get("content", "")
        
        if content.startswith("open ") or "file" in content.lower():
            for word in content.split():
                if word.startswith("/") or word.startswith("~"):
                    return word
    
    return None


def get_last_mentioned_project() -> Optional[str]:
    """Get the last mentioned project."""
    from app.memory import store
    
    facts = store.get_facts(category="project")
    
    if facts:
        return facts[0].get("content", "").split(" is ")[0]
    
    return None


def get_last_mentioned_person() -> Optional[str]:
    """Get the last mentioned person."""
    from app.memory import store
    
    facts = store.get_facts(category="person")
    
    if facts:
        return facts[0].get("content", "").split(" is ")[0]
    
    return None


def search_projects(project_name: str) -> List[Dict[str, Any]]:
    """Search for project-related memories."""
    from app.memory import store
    
    facts = store.get_facts(category="project")
    
    results = []
    for fact in facts:
        content = fact.get("content", "")
        if project_name.lower() in content.lower():
            results.append({"content": content})
    
    return results


def search_people(person_name: str) -> List[Dict[str, Any]]:
    """Search for person-related memories."""
    from app.memory import store
    
    facts = store.get_facts(category="person")
    
    results = []
    for fact in facts:
        content = fact.get("content", "")
        if person_name.lower() in content.lower():
            results.append({"content": content})
    
    return results