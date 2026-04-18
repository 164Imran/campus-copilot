import os
import subprocess
import datetime
from dotenv import load_dotenv, set_key

# LangChain et Bedrock
from langchain_aws import ChatBedrockConverse
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage

# Chargement de l'environnement depuis le dossier agent-booking
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_BOOKING_DIR = os.path.join(BASE_DIR, "agent-booking")
load_dotenv(os.path.join(AGENT_BOOKING_DIR, ".env"))

TUM_USERNAME = os.getenv("TUM_USERNAME")
TUM_PASSWORD = os.getenv("TUM_PASSWORD")

@tool
def book_study_room(booking_time: str, target_days_ahead: int) -> str:
    """
    Outil pour réserver une salle d'étude individuelle (Study Desk) à la bibliothèque de la TUM (Main Campus).
    Args:
        booking_time: Les horaires souhaités au format 'HH:MM:SS-HH:MM:SS' (ex: '09:00:00-13:00:00')
        target_days_ahead: Le nombre de jours dans le futur pour la réservation (ex: 1 pour demain, 2 pour après-demain)
    """
    print(f"🔧 Configuration de la réservation : {booking_time} (dans {target_days_ahead} jours)")
    
    engine_dir = os.path.join(AGENT_BOOKING_DIR, "manage-bookings")
    env_path = os.path.join(engine_dir, ".env")
    
    set_key(env_path, "USERNAME", TUM_USERNAME)
    set_key(env_path, "PASSWORD", TUM_PASSWORD)
    set_key(env_path, "SSO_PROVIDER", "tum")
    set_key(env_path, "TIMEZONE", "Europe/Berlin")
    set_key(env_path, "BOOKING_TIMES", booking_time)
    set_key(env_path, "TARGET_DAYS_AHEAD", str(target_days_ahead))
    set_key(env_path, "RESOURCE_URL_PATH", "/resources/study-desks-branch-library-main-campus/children")
    set_key(env_path, "SERVICE_ID", "601")
    
    try:
        result = subprocess.run(["python3", "book.py"], cwd=engine_dir, capture_output=True, text=True)
        return f"Succès: {result.stdout}" if result.returncode == 0 else f"Erreur: {result.stderr}\n{result.stdout}"
    except Exception as e:
        return f"Erreur système: {str(e)}"

@tool
def cancel_study_room(target_date: str) -> str:
    """
    Outil pour annuler une réservation existante.
    Args:
        target_date: La date de la réservation à annuler au format 'YYYY-MM-DD' (ex: '2026-04-21')
    """
    print(f"🔧 Configuration de l'annulation pour le : {target_date}")
    
    engine_dir = os.path.join(AGENT_BOOKING_DIR, "manage-bookings")
    env_path = os.path.join(engine_dir, ".env")
    
    set_key(env_path, "USERNAME", TUM_USERNAME)
    set_key(env_path, "PASSWORD", TUM_PASSWORD)
    set_key(env_path, "SSO_PROVIDER", "tum")
    set_key(env_path, "CANCEL_DATE", target_date)
    
    try:
        result = subprocess.run(["python3", "cancel.py"], cwd=engine_dir, capture_output=True, text=True)
        return f"Succès: {result.stdout}" if result.returncode == 0 else f"Erreur: {result.stderr}\n{result.stdout}"
    except Exception as e:
        return f"Erreur système: {str(e)}"

def run_room_agent(user_message):
    """Lance l'agent avec un message spécifié."""
    model_id = os.getenv("BEDROCK_MODEL_ID", "eu.anthropic.claude-sonnet-4-5-20250929-v1:0")
    llm = ChatBedrockConverse(model=model_id, temperature=0.0)
    tools = [book_study_room, cancel_study_room]
    llm_with_tools = llm.bind_tools(tools)

    today = datetime.datetime.now().strftime("%A %d %B %Y")
    sys_msg = f"Tu es un assistant IA très utile. Aujourd'hui nous sommes le {today}. Traduis les demandes d'horaires et de dates pour utiliser correctement tes outils `book_study_room` ou `cancel_study_room`. Pour annuler, utilise le format 'YYYY-MM-DD'."

    messages = [SystemMessage(content=sys_msg), HumanMessage(content=user_message)]
    
    print(f"🧠 Agent en cours de réflexion sur : '{user_message}'")
    ai_msg = llm_with_tools.invoke(messages)

    if ai_msg.tool_calls:
        for tool_call in ai_msg.tool_calls:
            if tool_call['name'] == 'book_study_room':
                return book_study_room.invoke(tool_call['args'])
            elif tool_call['name'] == 'cancel_study_room':
                return cancel_study_room.invoke(tool_call['args'])
    
    return ai_msg.content

if __name__ == "__main__":
    # Test rapide si lancé directement
    import sys
    if len(sys.argv) > 1:
        print(run_room_agent(sys.argv[1]))
