from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
import datetime
import json
from dotenv import load_dotenv

# Charger les variables d'environnement (.env) depuis la racine du projet
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

# Ajouter le dossier parent au path pour importer les agents
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from calendar_agent import sync_calendar, add_event, remove_event

app = FastAPI()

# Configuration CORS pour autoriser le front-end React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class EventCreate(BaseModel):
    summary: str
    start_time: str
    end_time: str
    location: str = "N/A"

class EventRemove(BaseModel):
    summary: str
    start_time: str

@app.post("/api/calendar/sync")
async def force_sync():
    """Force la synchronisation des sources (TUM, Salles, Manuel)."""
    try:
        sync_calendar.invoke({})
        return {"status": "synchronized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/calendar")
async def get_calendar():
    """Lit le fichier ICS et le convertit en JSON simple pour le front."""
    ics_path = os.path.join(os.path.dirname(__file__), "agent-calendar", "local_event.ics")
    if not os.path.exists(ics_path):
        # Déclencher une synchro si le fichier n'existe pas
        sync_calendar.invoke({})
    
    # On utilise icalendar pour parser le fichier
    from icalendar import Calendar
    try:
        with open(ics_path, 'rb') as f:
            gcal = Calendar.from_ical(f.read())
            events = []
            for component in gcal.walk():
                if component.name == "VEVENT":
                    # Extraction simplifiée des dates
                    start = component.get('dtstart').dt
                    end = component.get('dtend').dt
                    
                    # Convertir en string ISO
                    start_str = start.isoformat() if hasattr(start, 'isoformat') else str(start)
                    end_str = end.isoformat() if hasattr(end, 'isoformat') else str(end)

                    events.append({
                        "summary": str(component.get('summary')),
                        "start": start_str,
                        "end": end_str,
                        "location": str(component.get('location', 'N/A'))
                    })
            return events
    except Exception as e:
        # En cas d'erreur de lecture, on renvoie une liste vide ou l'erreur
        return {"error": str(e), "path": ics_path}

@app.post("/api/calendar/add")
async def api_add_event(event: EventCreate):
    try:
        res = add_event.invoke({
            "summary": event.summary,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "location": event.location
        })
        return {"status": "added", "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/calendar/remove")
async def api_remove_event(event: EventRemove):
    try:
        res = remove_event.invoke({
            "summary": event.summary,
            "start_time": event.start_time
        })
        return {"status": "removed", "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
