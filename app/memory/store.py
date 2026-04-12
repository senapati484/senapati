import os
import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

SENAPATI_HOME = os.path.expanduser("~/.senapati")
DB_PATH = os.path.join(SENAPATI_HOME, "memory/senapati.db")

_conn: Optional[sqlite3.Connection] = None


def get_db() -> sqlite3.Connection:
    """Get database connection."""
    global _conn
    
    if _conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _init_db()
    
    return _conn


def _init_db() -> None:
    """Initialize database schema."""
    conn = get_db()
    
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            summary TEXT,
            tags TEXT
        );
        
        CREATE TABLE IF NOT EXISTS turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
        
        CREATE VIRTUAL TABLE IF NOT EXISTS turns_fts USING fts5(
            content,
            content=turns,
            content_rowid=id
        );
        
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            created_at TEXT NOT NULL,
            last_seen TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            due_at TEXT,
            done INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool TEXT NOT NULL,
            args_json TEXT NOT NULL,
            weekday TEXT NOT NULL,
            hour INTEGER NOT NULL,
            count INTEGER DEFAULT 1,
            last_seen TEXT NOT NULL
        );
        
        CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);
        CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category);
        CREATE INDEX IF NOT EXISTS idx_facts_last_seen ON facts(last_seen);
        CREATE INDEX IF NOT EXISTS idx_tasks_done ON tasks(done);
    """)
    
    conn.commit()
    logger.info("Database initialized")


def create_session(session_id: str) -> None:
    """Create new session."""
    conn = get_db()
    
    conn.execute(
        "INSERT OR REPLACE INTO sessions (id, started_at) VALUES (?, ?)",
        (session_id, datetime.now().isoformat()),
    )
    conn.commit()


def close_session(session_id: str, summary: str = "", tags: str = "") -> None:
    """Close session with optional summary."""
    conn = get_db()
    
    conn.execute(
        "UPDATE sessions SET summary = ?, tags = ? WHERE id = ?",
        (summary, tags, session_id),
    )
    conn.commit()


def add_turn(session_id: str, role: str, content: str) -> int:
    """Add turn to session."""
    conn = get_db()
    
    cursor = conn.execute(
        "INSERT INTO turns (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, role, content, datetime.now().isoformat()),
    )
    conn.commit()
    
    turn_id = cursor.lastrowid
    
    conn.execute(
        "INSERT INTO turns_fts (rowid, content) VALUES (?, ?)",
        (turn_id, content),
    )
    conn.commit()
    
    return turn_id


def get_session_turns(session_id: str) -> List[Dict[str, Any]]:
    """Get all turns for a session."""
    conn = get_db()
    
    cursor = conn.execute(
        "SELECT role, content, timestamp FROM turns WHERE session_id = ? ORDER BY id",
        (session_id,),
    )
    
    return [
        {"role": row["role"], "content": row["content"], "timestamp": row["timestamp"]}
        for row in cursor.fetchall()
    ]


def get_recent_sessions(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent sessions."""
    conn = get_db()
    
    cursor = conn.execute(
        "SELECT id, started_at, summary FROM sessions ORDER BY started_at DESC LIMIT ?",
        (limit,),
    )
    
    return [
        {"id": row["id"], "started_at": row["started_at"], "summary": row["summary"]}
        for row in cursor.fetchall()
    ]


def save_fact(category: str, content: str, confidence: float = 1.0) -> int:
    """Save a fact."""
    conn = get_db()
    
    now = datetime.now().isoformat()
    
    cursor = conn.execute(
        "INSERT INTO facts (category, content, confidence, created_at, last_seen) VALUES (?, ?, ?, ?, ?)",
        (category, content, confidence, now, now),
    )
    conn.commit()
    
    return cursor.lastrowid


def get_facts(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get facts."""
    conn = get_db()
    
    if category:
        cursor = conn.execute(
            "SELECT id, category, content, confidence FROM facts WHERE category = ? ORDER BY last_seen DESC",
            (category,),
        )
    else:
        cursor = conn.execute(
            "SELECT id, category, content, confidence FROM facts ORDER BY last_seen DESC"
        )
    
    return [
        {"id": row["id"], "category": row["category"], "content": row["content"], "confidence": row["confidence"]}
        for row in cursor.fetchall()
    ]


def update_fact_seen(fact_id: int) -> None:
    """Update fact last_seen timestamp."""
    conn = get_db()
    
    conn.execute(
        "UPDATE facts SET last_seen = ? WHERE id = ?",
        (datetime.now().isoformat(), fact_id),
    )
    conn.commit()


def delete_fact(fact_id: int) -> None:
    """Delete a fact."""
    conn = get_db()
    
    conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
    conn.commit()


def add_task(description: str, due_at: Optional[str] = None) -> int:
    """Add a task."""
    conn = get_db()
    
    cursor = conn.execute(
        "INSERT INTO tasks (description, due_at, created_at) VALUES (?, ?, ?)",
        (description, due_at, datetime.now().isoformat()),
    )
    conn.commit()
    
    return cursor.lastrowid


def get_tasks(done: Optional[bool] = None) -> List[Dict[str, Any]]:
    """Get tasks."""
    conn = get_db()
    
    if done is None:
        cursor = conn.execute(
            "SELECT id, description, due_at, done, created_at FROM tasks ORDER BY created_at DESC"
        )
    elif done:
        cursor = conn.execute(
            "SELECT id, description, due_at, done, created_at FROM tasks WHERE done = 1 ORDER BY created_at DESC"
        )
    else:
        cursor = conn.execute(
            "SELECT id, description, due_at, done, created_at FROM tasks WHERE done = 0 ORDER BY created_at DESC"
        )
    
    return [
        {"id": row["id"], "description": row["description"], "due_at": row["due_at"], "done": bool(row["done"]), "created_at": row["created_at"]}
        for row in cursor.fetchall()
    ]


def complete_task(task_id: int) -> None:
    """Mark task as done."""
    conn = get_db()
    
    conn.execute(
        "UPDATE tasks SET done = 1 WHERE id = ?",
        (task_id,),
    )
    conn.commit()


def delete_task(task_id: int) -> None:
    """Delete a task."""
    conn = get_db()
    
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()


def record_habit(tool: str, args_json: str, weekday: str, hour: int) -> None:
    """Record a habit action."""
    conn = get_db()
    
    cursor = conn.execute(
        "SELECT id, count FROM habits WHERE tool = ? AND args_json = ? AND weekday = ? AND hour = ?",
        (tool, args_json, weekday, hour),
    )
    existing = cursor.fetchone()
    
    if existing:
        conn.execute(
            "UPDATE habits SET count = count + 1, last_seen = ? WHERE id = ?",
            (datetime.now().isoformat(), existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO habits (tool, args_json, weekday, hour, count, last_seen) VALUES (?, ?, ?, ?, 1, ?)",
            (tool, args_json, weekday, hour, datetime.now().isoformat()),
        )
    
    conn.commit()


def get_habits(weekday: str, hour: int) -> List[Dict[str, Any]]:
    """Get detected habits for current time."""
    conn = get_db()
    
    cursor = conn.execute(
        "SELECT tool, args_json, weekday, hour, count FROM habits WHERE weekday = ? AND hour = ? AND count >= 2",
        (weekday, hour),
    )
    
    return [
        {"tool": row["tool"], "args": json.loads(row["args_json"]), "count": row["count"]}
        for row in cursor.fetchall()
    ]


def search_turns(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search turns using FTS."""
    conn = get_db()
    
    try:
        cursor = conn.execute(
            "SELECT turns.content, turns.role, turns.timestamp FROM turns_fts JOIN turns ON turns_fts.rowid = turns.id WHERE turns_fts MATCH ? LIMIT ?",
            (query, limit),
        )
        
        return [
            {"content": row["content"], "role": row["role"], "timestamp": row["timestamp"]}
            for row in cursor.fetchall()
        ]
    except sqlite3.OperationalError:
        return get_turns_fallback(query, limit)


def get_turns_fallback(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fallback search using LIKE."""
    conn = get_db()
    
    cursor = conn.execute(
        "SELECT content, role, timestamp FROM turns WHERE content LIKE ? LIMIT ?",
        (f"%{query}%", limit),
    )
    
    return [
        {"content": row["content"], "role": row["role"], "timestamp": row["timestamp"]}
        for row in cursor.fetchall()
    ]


def compress_old_sessions(days: int = 14) -> int:
    """Compress sessions older than days into summaries."""
    conn = get_db()
    
    cutoff = datetime.now()
    from datetime import timedelta
    cutoff = cutoff - timedelta(days=days)
    
    cursor = conn.execute(
        "SELECT id, started_at FROM sessions WHERE started_at < ? AND summary IS NULL",
        (cutoff.isoformat(),),
    )
    
    count = 0
    for row in cursor.fetchall():
        session_id = row["id"]
        turns = get_session_turns(session_id)
        
        if turns:
            text = "\n".join([f"{t['role']}: {t['content']}" for t in turns])
            
            from app.prompts import build_session_summary_prompt
            
            from app.core import brain
            from app.prompts import parse_json_response
            
            prompt = build_session_summary_prompt(
                full_session_text=text,
                session_date=session_id[:8],
                session_duration="30m",
            )
            
            response = brain.generate(prompt, max_tokens=256)
            data = parse_json_response(response)
            
            summary = data.get("speak", text[:200])
            
            close_session(session_id, summary=summary[:500])
            count += 1
    
    return count


def close() -> None:
    """Close database connection."""
    global _conn
    
    if _conn:
        _conn.close()
        _conn = None