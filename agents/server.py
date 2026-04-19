from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
import datetime
import json

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# Ajouter le dossier parent au path pour importer les agents
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from calendar_agent import sync_calendar, add_event, remove_event

API_KEY = os.getenv("API_KEY")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]


def require_api_key(x_api_key: str = Header(None)):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

class EventCreate(BaseModel):
    summary: str
    start_time: str
    end_time: str
    location: str = "N/A"

class EventRemove(BaseModel):
    summary: str
    start_time: str

@app.post("/api/calendar/sync", dependencies=[Depends(require_api_key)])
async def force_sync():
    """Force la synchronisation des sources (TUM, Salles, Manuel)."""
    try:
        sync_calendar.invoke({})
        return {"status": "synchronized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/calendar", dependencies=[Depends(require_api_key)])
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
                    events.append({
                        "summary": str(component.get('summary')),
                        "start": component.get('dtstart').dt.isoformat(),
                        "end": component.get('dtend').dt.isoformat(),
                        "location": str(component.get('location', 'N/A'))
                    })
            return sorted(events, key=lambda x: x['start'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/calendar/add", dependencies=[Depends(require_api_key)])
async def create_event(event: EventCreate):
    """Appelle la fonction add_event de l'agent."""
    try:
        result = add_event.invoke({
            "summary": event.summary,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "location": event.location
        })
        return {"status": "success", "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/calendar/remove", dependencies=[Depends(require_api_key)])
async def delete_event(event: EventRemove):
    """Appelle la fonction remove_event de l'agent."""
    try:
        result = remove_event.invoke({
            "summary": event.summary,
            "start_time": event.start_time
        })
        return {"status": "success", "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
