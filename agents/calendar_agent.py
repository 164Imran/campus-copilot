import os
import sys
import json
import datetime

# Le client est maintenant dans agent-calendar/manage-calendar/
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(base_dir, "agent-calendar", "manage-calendar"))
from calendar_client import CalendarClient
from langchain_core.tools import tool

# Note: In a real project, we might want to share the .env loading logic
# For now, we assume the environment is already loaded by the main orchestrator

@tool
def get_user_schedule(days_ahead: int = 3) -> str:
    """
    Consulte l'emploi du temps de l'étudiant pour les prochains jours.
    Utile pour vérifier les disponibilités avant de réserver une salle.
    Args:
        days_ahead: Nombre de jours à consulter (défaut: 3).
    """
    url = os.getenv("TUM_ICAL_URL")
    if not url:
        return "Erreur: URL du calendrier non configurée (TUM_ICAL_URL)."
    
    client = CalendarClient(url)
    events = client.fetch_events(days_ahead)
    
    if not events:
        return f"Aucun événement trouvé pour les {days_ahead} prochains jours. Vous semblez libre !"
    
    report = f"Emploi du temps pour les {days_ahead} prochains jours :\n"
    for e in events:
        start_dt = datetime.datetime.fromisoformat(e['start'])
        # Convert to local time for display (assuming Berlin)
        report += f"- {start_dt.strftime('%A %d/%m à %H:%M')} : {e['summary']} ({e['location']})\n"
    
    return report

@tool
def sync_calendar():
    """
    Synchronise le calendrier local en fusionnant :
    1. L'emploi du temps TUMonline
    2. Les réservations de salles (reservation_history.json)
    3. Les événements manuels (manual_events.json)
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ics_path = os.path.join(base_dir, "agent-calendar", "local_event.ics")
    history_path = os.path.join(base_dir, "agent-booking", "reservation_history.json")
    manual_path = os.path.join(base_dir, "agent-calendar", "manual_events.json")
    url = os.getenv("TUM_ICAL_URL")

    from icalendar import Calendar, Event
    import pytz
    import json
    import requests

    # 1. Base : Calendrier TUM
    if url:
        try:
            response = requests.get(url, timeout=30)
            cal = Calendar.from_ical(response.content)
        except Exception as e:
            print(f"Erreur téléchargement TUM: {e}")
            cal = Calendar()
    else:
        cal = Calendar()

    # 2. Ajout des réservations de salles
    if os.path.exists(history_path):
        with open(history_path, 'r') as f:
            try:
                history = json.load(f)
                for res in history:
                    event = Event()
                    event.add('summary', 'Réservation Study Desk (TUM)')
                    start_str, end_str = res['time'].split('-')
                    start_dt = datetime.datetime.fromisoformat(f"{res['date']}T{start_str}").replace(tzinfo=pytz.timezone("Europe/Berlin"))
                    end_dt = datetime.datetime.fromisoformat(f"{res['date']}T{end_str}").replace(tzinfo=pytz.timezone("Europe/Berlin"))
                    event.add('dtstart', start_dt)
                    event.add('dtend', end_dt)
                    event.add('location', 'Library Main Campus')
                    cal.add_component(event)
            except Exception as e:
                print(f"[calendar] reservation history parse failed: {e}")

    # 3. Ajout des événements manuels
    if os.path.exists(manual_path):
        with open(manual_path, 'r') as f:
            try:
                manuals = json.load(f)
                for m in manuals:
                    event = Event()
                    event.add('summary', m['summary'])
                    event.add('dtstart', datetime.datetime.fromisoformat(m['start_time']).replace(tzinfo=pytz.timezone("Europe/Berlin")))
                    event.add('dtend', datetime.datetime.fromisoformat(m['end_time']).replace(tzinfo=pytz.timezone("Europe/Berlin")))
                    event.add('location', m.get('location', 'N/A'))
                    cal.add_component(event)
            except Exception as e:
                print(f"[calendar] manual events parse failed: {e}")

    with open(ics_path, 'wb') as f:
        f.write(cal.to_ical())
    
    return f"Calendrier fusionné généré dans {ics_path}"

@tool
def add_event(summary: str, start_time: str, end_time: str, location: str = "N/A"):
    """
    Ajoute manuellement un événement au calendrier.
    Args:
        summary: Titre de l'événement
        start_time: ISO format (ex: '2026-04-20T10:00:00')
        end_time: ISO format
        location: Lieu optionnel
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    manual_path = os.path.join(base_dir, "agent-calendar", "manual_events.json")
    
    events = []
    if os.path.exists(manual_path):
        with open(manual_path, 'r') as f:
            try:
                events = json.load(f)
            except Exception as e:
                print(f"[calendar] manual events load failed: {e}")
            
    events.append({
        "summary": summary,
        "start_time": start_time,
        "end_time": end_time,
        "location": location
    })
    
    with open(manual_path, 'w') as f:
        json.dump(events, f, indent=4)
        
    return sync_calendar.invoke({})


@tool
def remove_event(summary: str, start_time: str) -> str:
    """
    Supprime un événement manuel du calendrier.
    Args:
        summary: Le titre exact de l'événement à supprimer.
        start_time: La date de début au format ISO (ex: 2026-04-22T12:00:00).
    """
    manual_path = os.path.join(os.path.dirname(__file__), "agent-calendar", "manual_events.json")
    if not os.path.exists(manual_path):
        return "Aucun événement manuel trouvé."
    
    with open(manual_path, 'r') as f:
        events = json.load(f)
    
    # Filtrer pour garder tout SAUF l'événement cible
    new_events = [e for e in events if not (e['summary'] == summary and e['start_time'] == start_time)]
    
    if len(new_events) == len(events):
        return f"Événement '{summary}' non trouvé."
    
    with open(manual_path, 'w') as f:
        json.dump(new_events, f, indent=4)
    
    # Synchroniser pour mettre à jour le .ics
    sync_calendar.invoke({})
    return f"Événement '{summary}' supprimé avec succès."

if __name__ == "__main__":
    # Test
    from dotenv import load_dotenv
    # On charge l'environnement depuis la racine du projet
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    env_path = os.path.join(project_root, ".env")
    load_dotenv(env_path)
    
    # Test d'ajout manuel
    # print(add_event.invoke({
    #     "summary": "Mariage",
    #     "start_time": "2026-04-22T12:00:00",
    #     "end_time": "2026-04-22T13:30:00",
    #     "location": "Mensa"
    # }))
    
    # Pour appeler un outil décoré avec @tool, on utilise .invoke()
    # print(get_user_schedule.invoke({"days_ahead": 3}))
    
    # Test de synchronisation complète
    remove_event.invoke({"summary": "Déjeuner avec le Professeur", "start_time": "2026-04-22T12:00:00"})
    print(sync_calendar.invoke({}))

