# cognee_memory.py — mémoire persistante SQLite
import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("student_memory.db")


def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name TEXT UNIQUE,
            summary TEXT,
            topics TEXT,
            added_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_message TEXT,
            agents_called TEXT,
            response_summary TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()


_init_db()


def _extract_topics(summary: str) -> list:
    """Extrait des topics localement depuis les premières lignes du résumé — zéro API."""
    import re
    # Cherche les KEY POINTS ou bullet points dans le résumé structuré Bedrock
    lines = [l.strip() for l in summary.splitlines() if l.strip()]
    topics = []
    for line in lines:
        # Lignes de type "- What it is" ou "## KEY POINTS"
        clean = re.sub(r"^[-•*#]+\s*", "", line)
        clean = re.sub(r"\*+", "", clean).strip()
        if 4 < len(clean) < 80 and not clean.startswith("http"):
            topics.append(clean)
        if len(topics) >= 5:
            break
    return topics if topics else [summary[:80]]


async def remember_course(course_name: str, summary: str, pdf_content: str = ""):
    safe_name = str(course_name)[:100]
    safe_summary = str(summary)[:800]

    conn = sqlite3.connect(DB_PATH)
    existing = conn.execute(
        "SELECT topics FROM courses WHERE course_name = ?", (safe_name,)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE courses SET summary = ?, added_at = ? WHERE course_name = ?",
            (safe_summary, datetime.now().isoformat(), safe_name)
        )
        conn.commit()
        conn.close()
        return
    topics = _extract_topics(safe_summary)
    conn.execute(
        "INSERT INTO courses (course_name, summary, topics, added_at) VALUES (?, ?, ?, ?)",
        (safe_name, safe_summary, json.dumps(topics, ensure_ascii=False), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


async def get_student_context(question: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    courses = conn.execute(
        "SELECT course_name, summary, topics FROM courses"
    ).fetchall()
    recent_interactions = conn.execute(
        "SELECT user_message, agents_called, timestamp FROM interactions ORDER BY id DESC LIMIT 5"
    ).fetchall()
    conn.close()

    parts = []
    if courses:
        parts.append("Cours mémorisés depuis Moodle :")
        for name, summary, topics_json in courses:
            try:
                topics = json.loads(topics_json)
                parts.append(f"  • {name} → {', '.join(topics)}")
            except Exception:
                parts.append(f"  • {name}")

    if recent_interactions:
        parts.append("Historique récent :")
        for msg, agents_json, ts in recent_interactions:
            try:
                agents = json.loads(agents_json)
                parts.append(f"  • [{ts[:10]}] \"{msg[:70]}\" → agents: {agents}")
            except Exception:
                parts.append(f"  • [{ts[:10]}] \"{msg[:70]}\"")

    if not parts:
        return "Première interaction — aucun historique disponible."
    return "\n".join(parts)


async def log_interaction(user_message: str, agents_called: list, response: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO interactions (user_message, agents_called, response_summary, timestamp) VALUES (?, ?, ?, ?)",
        (user_message[:500], json.dumps(agents_called), response[:200], datetime.now().isoformat())
    )
    conn.execute("""
        DELETE FROM interactions WHERE id NOT IN (
            SELECT id FROM interactions ORDER BY id DESC LIMIT 100
        )
    """)
    conn.commit()
    conn.close()


def get_memory_summary() -> dict:
    conn = sqlite3.connect(DB_PATH)
    courses = conn.execute(
        "SELECT course_name, topics, added_at FROM courses"
    ).fetchall()
    interaction_count = conn.execute(
        "SELECT COUNT(*) FROM interactions"
    ).fetchone()[0]
    conn.close()

    return {
        "memory_engine": "sqlite",
        "courses_memorized": [
            {
                "name": c[0],
                "topics": json.loads(c[1]) if c[1] else [],
                "since": c[2][:10] if c[2] else "",
            }
            for c in courses
        ],
        "total_interactions": interaction_count,
    }
