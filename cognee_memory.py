# cognee_memory.py
import asyncio
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Tentative d'import Cognee avec configuration Bedrock/Anthropic ─
COGNEE_AVAILABLE = False

try:
    import cognee
    from cognee import SearchType

    # Cognee a besoin d'un LLM provider — on pointe vers Anthropic direct
    # (plus simple que Bedrock pour Cognee en 48h)
    os.environ["LLM_API_KEY"] = os.getenv("ANTHROPIC_API_KEY", "")
    os.environ["LLM_PROVIDER"] = "anthropic"
    os.environ["LLM_MODEL"] = "claude-sonnet-4-5"
    os.environ["EMBEDDING_PROVIDER"] = "openai"
    os.environ["EMBEDDING_MODEL"] = "text-embedding-3-small"

    if os.getenv("ANTHROPIC_API_KEY"):
        COGNEE_AVAILABLE = True
        print("✅ Cognee actif (Anthropic)")
    else:
        print("⚠️ Cognee installé mais ANTHROPIC_API_KEY manquante — fallback SQLite")
except ImportError:
    print("⚠️ Cognee non installé — fallback SQLite actif")


# ── Base SQLite locale (fallback + toujours utilisé pour les interactions) ──
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


# ── Fonction interne : extraire les topics clés d'un résumé ───────
def _extract_topics(course_name: str, summary: str) -> list:
    from bedrock_client import call_claude
    raw = call_claude(
        prompt=f"""
Extrait les 5 concepts clés de ce cours universitaire.
Cours : {course_name}
Résumé : {summary}

Réponds UNIQUEMENT avec un JSON array de strings, sans explication.
Exemple : ["intégrales", "séries de Taylor", "convergence"]
        """,
        system_prompt="Tu extrais des concepts académiques. JSON array uniquement."
    )
    try:
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)
    except Exception:
        return [summary[:60]]


# ── API publique ───────────────────────────────────────────────────

async def remember_course(course_name: str, summary: str, pdf_content: str = ""):
    """
    À appeler juste après run_moodle_agent().
    Indexe un cours dans la mémoire persistante de l'étudiant.
    """
    # Tentative Cognee (graphe sémantique riche)
    if COGNEE_AVAILABLE:
        try:
            content = f"Cours universitaire: {course_name}\n\nRésumé: {summary}"
            if pdf_content:
                content += f"\n\nContenu complet: {pdf_content[:2000]}"
            await cognee.add(content, dataset_name="student_courses")
            await cognee.cognify()
            print(f"🧠 Cognee: '{course_name}' indexé dans le graphe")
        except Exception as e:
            print(f"⚠️ Cognee échoué ({e})")

    # Toujours stocker dans SQLite (fiable, rapide, démo-safe)
    topics = _extract_topics(course_name, summary)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO courses (course_name, summary, topics, added_at) VALUES (?, ?, ?, ?)",
        (course_name, summary, json.dumps(topics, ensure_ascii=False), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    print(f"🗃️ SQLite: '{course_name}' mémorisé → topics: {topics}")


async def get_student_context(question: str) -> str:
    """
    À appeler AVANT de générer le plan de révision.
    Retourne ce que l'agent sait déjà de l'étudiant, en lien avec sa question.
    """
    context_parts = []

    # Tentative Cognee (recherche sémantique dans le graphe)
    if COGNEE_AVAILABLE:
        try:
            results = await cognee.search(SearchType.INSIGHTS, query=question)
            if results:
                context_parts.append(f"[Cognee graph] {str(results)[:400]}")
        except Exception as e:
            print(f"⚠️ Cognee search échoué ({e})")

    # Toujours compléter avec SQLite
    conn = sqlite3.connect(DB_PATH)
    courses = conn.execute(
        "SELECT course_name, summary, topics FROM courses"
    ).fetchall()
    recent_interactions = conn.execute(
        "SELECT user_message, agents_called, timestamp FROM interactions ORDER BY id DESC LIMIT 5"
    ).fetchall()
    conn.close()

    if courses:
        context_parts.append("Cours mémorisés depuis Moodle :")
        for name, summary, topics_json in courses:
            try:
                topics = json.loads(topics_json)
                context_parts.append(f"  • {name} → {', '.join(topics)}")
            except Exception:
                context_parts.append(f"  • {name}")

    if recent_interactions:
        context_parts.append("Historique récent :")
        for msg, agents_json, ts in recent_interactions:
            try:
                agents = json.loads(agents_json)
                context_parts.append(f"  • [{ts[:10]}] \"{msg[:70]}\" → agents: {agents}")
            except Exception:
                context_parts.append(f"  • [{ts[:10]}] \"{msg[:70]}\"")

    if not context_parts:
        return "Première interaction — aucun historique disponible."

    return "\n".join(context_parts)


async def log_interaction(user_message: str, agents_called: list, response: str):
    """
    À appeler à la fin de chaque run_orchestrator().
    Construit l'historique pour détecter les patterns et personnaliser.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO interactions (user_message, agents_called, response_summary, timestamp) VALUES (?, ?, ?, ?)",
        (user_message, json.dumps(agents_called), response[:200], datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_memory_summary() -> dict:
    """Retourne l'état complet de la mémoire — utile pour /memory endpoint ou démo."""
    conn = sqlite3.connect(DB_PATH)
    courses = conn.execute(
        "SELECT course_name, topics, added_at FROM courses"
    ).fetchall()
    interaction_count = conn.execute(
        "SELECT COUNT(*) FROM interactions"
    ).fetchone()[0]
    conn.close()

    return {
        "memory_engine": "cognee + sqlite" if COGNEE_AVAILABLE else "sqlite",
        "courses_memorized": [
            {
                "name": c[0],
                "topics": json.loads(c[1]),
                "since": c[2][:10]
            }
            for c in courses
        ],
        "total_interactions": interaction_count,
    }


# ── Test standalone ────────────────────────────────────────────────
if __name__ == "__main__":
    async def _test():
        print("\n=== Test mémoire Campus Co-Pilot ===\n")

        await remember_course(
            "Analysis 1",
            "Intégrales de Riemann, convergence des séries, suites de Cauchy.",
        )
        await remember_course(
            "Linear Algebra",
            "Décomposition en valeurs propres, diagonalisation, espaces vectoriels.",
        )

        print("\n--- Contexte pour question maths ---")
        ctx = await get_student_context("j'ai du mal avec les intégrales")
        print(ctx)

        await log_interaction(
            "Aide-moi pour mon exam de maths",
            ["moodle", "agenda", "room"],
            "Plan de révision créé, 3 sessions planifiées, salle réservée."
        )

        print("\n--- Résumé mémoire ---")
        summary = get_memory_summary()
        print(json.dumps(summary, indent=2, ensure_ascii=False))

    asyncio.run(_test())
