# orchestrator.py
import asyncio
import json
from bedrock_client import call_claude
from cognee_memory import remember_course, get_student_context, log_interaction

# ── Mocks de secours si les agents ne sont pas prêts ──────────────
def mock_moodle():
    return [
        {
            "course": "Analysis 1",
            "pdf_path": "/tmp/mock_analysis1.pdf",
            "pdf_filename": "analysis1_week10.pdf",
            "summary": "[MOCK] Résumé : Intégrales de Riemann, convergence des séries.",
        },
        {
            "course": "Linear Algebra",
            "pdf_path": "/tmp/mock_linalg.pdf",
            "pdf_filename": "linalg_week10.pdf",
            "summary": "[MOCK] Résumé : Décomposition en valeurs propres, diagonalisation.",
        },
    ]

def mock_agenda(moodle_results):
    return {"new_deadlines": 2, "ics_url": "http://mock.url/calendar.ics"}

def mock_room(user_message):
    return {"message": "[MOCK] Salle MI 03.08.011 réservée demain à 14h", "ref": "TUM-MOCK-001"}


# ── Chargement des vrais agents avec fallback ──────────────────────
def load_agent(name):
    """
    Tente d'importer l'agent demandé.
    Retourne None si l'agent n'est pas encore implémenté ou plante à l'import.

    Interface attendue par agent :
      moodle : run_moodle_agent() -> list[dict]
               chaque dict : {course, pdf_path, pdf_filename, summary}
      agenda : run_agenda_agent(moodle_data: list[dict]) -> dict
               retour : {new_deadlines, ics_url, ...}
      room   : run_room_agent(user_message: str) -> dict
               retour : {message, ref, tool}
    """
    try:
        if name == "moodle":
            from agents.moodle_agent import run_moodle_agent
            return run_moodle_agent
        elif name == "agenda":
            from agents.agenda_agent import run_agenda_agent
            return run_agenda_agent
        elif name == "room":
            from agents.room_agent import run_room_agent
            return run_room_agent
    except Exception as e:
        print(f"⚠️ Impossible de charger l'agent '{name}': {type(e).__name__}: {e}")
        return None


# ── Étape 1 : Routing ──────────────────────────────────────────────
def decide_agents(user_message: str) -> list:
    response = call_claude(
        prompt=f"""
Analyse cette demande étudiante et décide quels agents appeler.
Réponds UNIQUEMENT en JSON valide, rien d'autre.

Agents disponibles :
- "moodle"  : résumer des cours, slides, fichiers Moodle
- "agenda"  : deadlines, calendrier, dates
- "room"    : réserver une salle, espace de travail

Exemples :
"résume mes cours" → {{"agents": ["moodle", "agenda"]}}
"réserve une salle" → {{"agents": ["room"]}}
"résume et réserve" → {{"agents": ["moodle", "agenda", "room"]}}
"mes deadlines" → {{"agents": ["agenda"]}}

Demande : {user_message}
        """,
        system_prompt="Tu es un router d'agents. Réponds uniquement en JSON valide."
    )

    try:
        clean = response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)["agents"]
    except Exception:
        print(f"⚠️ Routing échoué, fallback sur moodle. Réponse brute : {response}")
        return ["moodle"]


# ── Étape 2 : Exécution des agents ────────────────────────────────
def run_agents(agents: list, user_message: str) -> dict:
    results = {}

    if "moodle" in agents:
        print("📚 Agent Moodle...")
        fn = load_agent("moodle")
        try:
            results["moodle"] = fn() if fn else mock_moodle()
        except Exception as e:
            print(f"⚠️ Moodle échoué ({e}), mock activé")
            results["moodle"] = mock_moodle()

        # Mémoriser les cours extraits
        for course in results["moodle"]:
            asyncio.run(remember_course(
                course.get("course", "Inconnu"),
                course.get("summary", "")
            ))

    if "agenda" in agents:
        print("📅 Agent Agenda...")
        fn = load_agent("agenda")
        moodle_data = results.get("moodle", [])
        try:
            results["agenda"] = fn(moodle_data) if fn else mock_agenda(moodle_data)
        except Exception as e:
            print(f"⚠️ Agenda échoué ({e}), mock activé")
            results["agenda"] = mock_agenda(moodle_data)

    if "room" in agents:
        print("🏫 Agent Room...")
        fn = load_agent("room")
        try:
            results["room"] = fn(user_message) if fn else mock_room(user_message)
        except Exception as e:
            print(f"⚠️ Room échoué ({e}), mock activé")
            results["room"] = mock_room(user_message)

    return results


# ── Étape 3 : Synthèse finale ──────────────────────────────────────
def synthesize(results: dict) -> str:
    if not results:
        return "Je n'ai pas pu traiter ta demande. Essaie de reformuler."

    results_text = json.dumps(results, ensure_ascii=False, indent=2)

    return call_claude(
        prompt=f"""
Voici les résultats des agents IA :
{results_text}

Génère une réponse claire, amicale et concise pour un étudiant TUM.
Maximum 4 phrases. Pas de JSON, juste du texte naturel.
        """,
        system_prompt="Tu es un assistant étudiant bienveillant et concis."
    )


# ── Point d'entrée principal ───────────────────────────────────────
def run_orchestrator(user_message: str) -> dict:
    print(f"\n{'='*50}")
    print(f"🎯 Demande : {user_message}")

    # Récupère le contexte mémorisé AVANT de router
    memory_context = asyncio.run(get_student_context(user_message))
    print(f"🧠 Contexte mémoire : {memory_context[:100]}...")

    agents = decide_agents(user_message)
    print(f"🤖 Agents sélectionnés : {agents}")

    results = run_agents(agents, user_message)
    results["memory_context"] = memory_context  # injecté dans la synthèse
    response = synthesize(results)

    # Log l'interaction pour la session suivante
    asyncio.run(log_interaction(user_message, agents, response))

    print(f"✅ Réponse : {response}")
    print(f"{'='*50}\n")

    return {
        "response": response,
        "agents_called": agents,
        "raw_results": results
    }


# ── Tests ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        "Réserve-moi une salle près du bâtiment maths demain à 14h",
        "Résume mes nouveaux cours de maths",
        "Quelles sont mes deadlines cette semaine ?",
        "Résume mes cours, ajoute les deadlines et réserve une salle demain à 14h"
    ]

    for test in tests:
        run_orchestrator(test)
