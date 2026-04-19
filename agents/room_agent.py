import os
import sys
import json
import subprocess
import datetime
from dotenv import load_dotenv, dotenv_values, set_key

from langchain_aws import ChatBedrockConverse
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_BOOKING_DIR = os.path.join(BASE_DIR, "agent-booking")
MANAGE_BOOKINGS_DIR = os.path.join(AGENT_BOOKING_DIR, "manage-bookings")

load_dotenv(os.path.join(BASE_DIR, "..", ".env"))

TUM_USERNAME = os.getenv("TUM_USERNAME")
TUM_PASSWORD = os.getenv("TUM_PASSWORD")

if not TUM_USERNAME or not TUM_PASSWORD:
    mb_env = dotenv_values(os.path.join(MANAGE_BOOKINGS_DIR, ".env"))
    TUM_USERNAME = TUM_USERNAME or mb_env.get("USERNAME")
    TUM_PASSWORD = TUM_PASSWORD or mb_env.get("PASSWORD")

# Dossiers de données
AGENT_BOOKING_DIR = os.path.join(BASE_DIR, "agent-booking")
HISTORY_FILE = os.path.join(AGENT_BOOKING_DIR, "reservation_history.json")
CHAT_HISTORY_FILE = os.path.join(AGENT_BOOKING_DIR, "chat_history.json")
CHAT_HISTORY_MAX = 20  # messages max conservés


def log_reservation(date: str, time: str):
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            try:
                history = json.load(f)
            except Exception:
                pass
    history.append({"date": date, "time": time, "timestamp": datetime.datetime.now().isoformat()})
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def load_chat_history(limit: int = 10) -> list:
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r") as f:
            try:
                history = json.load(f)
                # Sanitise le contenu avant de le réinjecter dans le LLM
                safe = [
                    {"role": m["role"], "content": str(m.get("content", ""))[:500]}
                    for m in history
                    if m.get("role") in ("user", "assistant")
                ]
                return safe[-limit:]
            except Exception:
                pass
    return []


def save_chat_message(role: str, content: str):
    history = []
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r") as f:
            try:
                history = json.load(f)
            except Exception:
                pass
    history.append({"role": role, "content": str(content)[:500]})
    # Rotation : limite la taille du fichier
    history = history[-CHAT_HISTORY_MAX:]
    with open(CHAT_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def get_recent_reservations(limit: int = 5) -> list:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            try:
                history = json.load(f)
                return history[-limit:]
            except Exception:
                pass
    return []


@tool
def book_study_room(booking_time: str, target_days_ahead: int) -> str:
    """
    Outil pour réserver une salle d'étude individuelle (Study Desk) à la bibliothèque de la TUM.
    Args:
        booking_time: Horaires au format 'HH:MM:SS-HH:MM:SS' (ex: '09:00:00-11:00:00')
        target_days_ahead: Jours dans le futur (ex: 1 pour demain). Max: 4.
    """
    if target_days_ahead > 4:
        return "Impossible de réserver plus de 4 jours à l'avance (limite TUM)."
    if target_days_ahead < 0:
        return "Impossible de réserver dans le passé."

    print(f"🔧 Réservation : {booking_time} dans {target_days_ahead} jour(s)")

    engine_dir = MANAGE_BOOKINGS_DIR
    env_path = os.path.join(engine_dir, ".env")

    if TUM_USERNAME:
        set_key(env_path, "USERNAME", TUM_USERNAME)
    if TUM_PASSWORD:
        set_key(env_path, "PASSWORD", TUM_PASSWORD)
    set_key(env_path, "SSO_PROVIDER", "tum")
    set_key(env_path, "TIMEZONE", "Europe/Berlin")
    set_key(env_path, "BOOKING_TIMES", booking_time)
    set_key(env_path, "TARGET_DAYS_AHEAD", str(target_days_ahead))
    set_key(env_path, "RESOURCE_URL_PATH", "/resources/study-desks-branch-library-main-campus/children")
    set_key(env_path, "SERVICE_ID", "601")

    try:
        result = subprocess.run(
            [sys.executable, "book.py"], cwd=engine_dir,
            capture_output=True, text=True, timeout=120,
        )
        output = (result.stdout + result.stderr).lower()
        if result.returncode == 0 and ("success" in output or "successful" in output):
            res_date = (datetime.datetime.now() + datetime.timedelta(days=target_days_ahead)).strftime("%Y-%m-%d")
            log_reservation(res_date, booking_time)
            return f"Succès: Réservation effectuée pour le {res_date} à {booking_time}."
        return f"Erreur: {result.stderr}\n{result.stdout}"
    except subprocess.TimeoutExpired:
        return "Erreur: la réservation a pris trop de temps (timeout 120s)."
    except Exception as e:
        return f"Erreur système: {str(e)}"


@tool
def cancel_study_room(target_date: str) -> str:
    """
    Outil pour annuler une réservation existante.
    Args:
        target_date: Date de la réservation au format 'YYYY-MM-DD' (ex: '2026-04-21')
    """
    print(f"🔧 Annulation pour le : {target_date}")

    engine_dir = MANAGE_BOOKINGS_DIR
    env_path = os.path.join(engine_dir, ".env")

    if TUM_USERNAME:
        set_key(env_path, "USERNAME", TUM_USERNAME)
    if TUM_PASSWORD:
        set_key(env_path, "PASSWORD", TUM_PASSWORD)
    set_key(env_path, "SSO_PROVIDER", "tum")
    set_key(env_path, "CANCEL_DATE", target_date)

    try:
        result = subprocess.run(
            [sys.executable, "cancel.py"], cwd=engine_dir,
            capture_output=True, text=True, timeout=120,
        )
        return f"Succès: {result.stdout}" if result.returncode == 0 else f"Erreur: {result.stderr}\n{result.stdout}"
    except subprocess.TimeoutExpired:
        return "Erreur: l'annulation a pris trop de temps (timeout 120s)."
    except Exception as e:
        return f"Erreur système: {str(e)}"


def run_room_agent(user_message: str) -> dict:
    """Lance l'agent booking. Retourne un dict {message, ref, tool}."""
    model_id = os.getenv("BEDROCK_MODEL_ID", "eu.anthropic.claude-sonnet-4-5-20250929-v1:0")
    llm = ChatBedrockConverse(model=model_id, temperature=0.0)
    llm_with_tools = llm.bind_tools([book_study_room, cancel_study_room])

    today = datetime.datetime.now().strftime("%A %d %B %Y")

    recent_res = get_recent_reservations()
    history_context = ""
    if recent_res:
        history_context = "\n\nHistorique de tes réservations récentes :\n"
        for r in recent_res:
            history_context += f"- {r['date']} à {r['time']}\n"

    sys_msg = (
        f"Tu es un assistant IA très utile. Aujourd'hui nous sommes le {today}. "
        f"Traduis les demandes d'horaires et de dates pour utiliser `book_study_room` ou `cancel_study_room`. "
        f"Si l'heure de fin n'est pas précisée, réserve 2h. "
        f"Pour annuler, utilise le format 'YYYY-MM-DD'. "
        f"N'attends jamais de confirmation, agis directement.{history_context}"
    )

    chat_history = load_chat_history()
    messages = [SystemMessage(content=sys_msg)]
    for m in chat_history:
        if m["role"] == "user":
            messages.append(HumanMessage(content=m["content"]))
        else:
            messages.append(AIMessage(content=m["content"]))
    messages.append(HumanMessage(content=user_message))

    print(f"🧠 Agent en cours de réflexion sur : '{user_message}'")
    ai_msg = llm_with_tools.invoke(messages)
    response_content = ai_msg.content or ""
    tool_used = None

    if ai_msg.tool_calls:
        for tool_call in ai_msg.tool_calls:
            if tool_call["name"] == "book_study_room":
                response_content = book_study_room.invoke(tool_call["args"])
                tool_used = "book_study_room"
            elif tool_call["name"] == "cancel_study_room":
                response_content = cancel_study_room.invoke(tool_call["args"])
                tool_used = "cancel_study_room"

    save_chat_message("user", user_message)
    save_chat_message("assistant", str(response_content))

    return {"message": response_content, "ref": "TUM-LIVE" if tool_used else None, "tool": tool_used}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(run_room_agent(" ".join(sys.argv[1:])))
