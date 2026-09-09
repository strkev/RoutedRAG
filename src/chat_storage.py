import os
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from src.logger import logger

DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "chats.db")

def get_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                personality TEXT DEFAULT 'default',
                dynamic_model INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model_used TEXT,
                tool_calls TEXT,
                token_usage TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (chat_id) REFERENCES chats (id) ON DELETE CASCADE
            )
        """)
        cursor = conn.execute("PRAGMA table_info(messages)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "token_usage" not in columns:
            try:
                conn.execute("ALTER TABLE messages ADD COLUMN token_usage TEXT")
            except Exception as e:
                logger.debug(f"[DB] Migration note: {e}")
        conn.commit()

def generate_title(content: str) -> str:
    cleaned = content.strip().replace("\n", " ")
    if len(cleaned) <= 36:
        return cleaned or "Neuer Chat"
    truncated = cleaned[:36]
    last_space = truncated.rfind(" ")
    if last_space > 15:
        return truncated[:last_space] + "..."
    return truncated + "..."

def create_chat(chat_id: str, title: Optional[str] = None, personality: str = "default", dynamic_model: bool = True) -> Dict[str, Any]:
    now = datetime.utcnow().isoformat()
    final_title = title or "Neuer Chat"
    with get_db() as conn:
        conn.execute(
            "INSERT INTO chats (id, title, personality, dynamic_model, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, final_title, personality, 1 if dynamic_model else 0, now, now)
        )
        conn.commit()
    return {
        "id": chat_id,
        "title": final_title,
        "personality": personality,
        "dynamic_model": dynamic_model,
        "created_at": now,
        "updated_at": now
    }

def get_chat(chat_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        chat_row = conn.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat_row:
            return None
        
        msg_rows = conn.execute(
            "SELECT * FROM messages WHERE chat_id = ? ORDER BY id ASC", 
            (chat_id,)
        ).fetchall()
        
        messages = []
        for m in msg_rows:
            tool_calls = None
            if m["tool_calls"]:
                try:
                    tool_calls = json.loads(m["tool_calls"])
                except Exception:
                    tool_calls = []

            token_usage = None
            if "token_usage" in m.keys() and m["token_usage"]:
                try:
                    token_usage = json.loads(m["token_usage"])
                except Exception:
                    token_usage = None

            messages.append({
                "id": m["id"],
                "role": m["role"],
                "content": m["content"],
                "model_used": m["model_used"],
                "tool_calls": tool_calls,
                "token_usage": token_usage,
                "created_at": m["created_at"]
            })
            
        return {
            "id": chat_row["id"],
            "title": chat_row["title"],
            "personality": chat_row["personality"],
            "dynamic_model": bool(chat_row["dynamic_model"]),
            "created_at": chat_row["created_at"],
            "updated_at": chat_row["updated_at"],
            "messages": messages
        }

def list_chats(limit: int = 10, offset: int = 0) -> Dict[str, Any]:
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM chats").fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM chats ORDER BY updated_at DESC LIMIT ? OFFSET ?", 
            (limit, offset)
        ).fetchall()
        
        chats = []
        for r in rows:
            last_msg = conn.execute(
                "SELECT content FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT 1",
                (r["id"],)
            ).fetchone()
            preview = last_msg["content"][:60] if last_msg else ""
            
            chats.append({
                "id": r["id"],
                "title": r["title"],
                "personality": r["personality"],
                "dynamic_model": bool(r["dynamic_model"]),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "preview": preview
            })
            
        has_more = (offset + limit) < total
        return {
            "chats": chats,
            "total": total,
            "has_more": has_more,
            "offset": offset,
            "limit": limit
        }

def save_message(
    chat_id: str, 
    role: str, 
    content: str, 
    model_used: Optional[str] = None, 
    tool_calls: Optional[List[Dict[str, Any]]] = None,
    token_usage: Optional[Dict[str, Any]] = None,
    personality: Optional[str] = None,
    dynamic_model: Optional[bool] = None
) -> int:
    now = datetime.utcnow().isoformat()
    serialized_tools = json.dumps(tool_calls) if tool_calls else None
    serialized_tokens = json.dumps(token_usage) if token_usage else None
    
    with get_db() as conn:
        chat = conn.execute("SELECT id, title FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat:
            title = generate_title(content) if role == "user" else "Neuer Chat"
            p = personality or "default"
            dm = 1 if (dynamic_model is None or dynamic_model) else 0
            conn.execute(
                "INSERT INTO chats (id, title, personality, dynamic_model, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (chat_id, title, p, dm, now, now)
            )
        elif chat["title"] == "Neuer Chat" and role == "user":
            new_title = generate_title(content)
            conn.execute("UPDATE chats SET title = ? WHERE id = ?", (new_title, chat_id))

        cursor = conn.execute(
            "INSERT INTO messages (chat_id, role, content, model_used, tool_calls, token_usage, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (chat_id, role, content, model_used, serialized_tools, serialized_tokens, now)
        )
        conn.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now, chat_id))
        conn.commit()
        return cursor.lastrowid

def rename_chat(chat_id: str, new_title: str) -> bool:
    with get_db() as conn:
        cursor = conn.execute("UPDATE chats SET title = ?, updated_at = ? WHERE id = ?", 
                              (new_title, datetime.utcnow().isoformat(), chat_id))
        conn.commit()
        return cursor.rowcount > 0

def delete_chat(chat_id: str) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        cursor = conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        conn.commit()
        return cursor.rowcount > 0

init_db()
