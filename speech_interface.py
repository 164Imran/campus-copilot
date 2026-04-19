import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import websockets
from text_speech import generate_audio_bytes
import orchestrator
from aws import s3_client as s3
from pydantic import BaseModel
import sys

# Ajouter le dossier agents au path pour les imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents"))
from agents.calendar_agent import sync_calendar, add_event, remove_event

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REMPLACE PAR TA CLÉ DEEPGRAM (Gratiut 200$)
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # URL Deepgram : Plus rapide et plus tolérant que ElevenLabs pour le live
    dg_url = "wss://api.deepgram.com/v1/listen?language=fr&model=nova-2&smart_format=true"
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

    try:
        async with websockets.connect(dg_url, additional_headers=headers) as dg_ws:
            print("🚀 Deepgram connecté (Instance STT Live)")

            async def receive_from_dg():
                try:
                    async for message in dg_ws:
                        data = json.loads(message)
                        transcript = data.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "")
                        
                        if transcript:
                            is_final = data.get("is_final", False)
                            try:
                                await websocket.send_json({"type": "stt", "text": transcript, "is_final": is_final})
                            except Exception:
                                break # Le client est déconnecté

                            if is_final:
                                pass
                except websockets.exceptions.ConnectionClosed:
                    print("Deepgram a fermé la connexion.")
                except Exception as e:
                    print(f"Info receive_from_dg: {e}")

            async def send_to_dg():
                try:
                    while True:
                        msg = await websocket.receive()
                        if "bytes" in msg and msg.get("bytes"):
                            await dg_ws.send(msg["bytes"])
                        elif "text" in msg and msg.get("text"):
                            data = json.loads(msg["text"])
                            if data.get("type") == "process":
                                print(f"🚀 Envoi vers l'Orchestrateur du texte : {data['text']}")
                                
                                async def process_orchestrator_and_tts(text_input):
                                    try:
                                        result = await orchestrator.run_orchestrator(text_input, session_id="voice-session")
                                        full_text = result["response"]
                                        
                                        import re
                                        sentences = re.split(r'([.!?\n:])', full_text)
                                        
                                        combined_sentences = []
                                        temp_sentence = ""
                                        for part in sentences:
                                            temp_sentence += part
                                            if any(p in part for p in ['.', '!', '?', '\n', ':']):
                                                if temp_sentence.strip():
                                                    combined_sentences.append(temp_sentence.strip())
                                                temp_sentence = ""
                                        if temp_sentence.strip():
                                            combined_sentences.append(temp_sentence.strip())
                                            
                                        try:
                                            await websocket.send_json({
                                                "type": "agent", 
                                                "text": full_text,
                                                "sentences": combined_sentences
                                            })
                                        except Exception:
                                            return
                                            
                                        for sentence in combined_sentences:
                                            if sentence.strip():
                                                print(f"🔊 Génération audio pour : {sentence.strip()}")
                                                audio_bytes = await asyncio.to_thread(generate_audio_bytes, sentence.strip())
                                                if audio_bytes:
                                                    try:
                                                        await websocket.send_bytes(audio_bytes)
                                                    except Exception as e:
                                                        print(f"Client déconnecté pendant TTS: {e}")
                                                        break
                                    except Exception as e:
                                        print(f"Erreur avec l'Orchestrateur: {e}")

                                asyncio.create_task(process_orchestrator_and_tts(data["text"]))
                except Exception as e:
                    print(f"Info send_to_dg: {e}")

            await asyncio.gather(receive_from_dg(), send_to_dg())
    except Exception as e:
        print(f"❌ Erreur : {e}")

@app.get("/api/summary/{course}/{filename}")
async def get_summary_api(course: str, filename: str):
    s3_key = f"summaries/{course}/{filename}"
    data = s3._get_json(s3_key)
    if data and "summary" in data:
        return {"summary": data["summary"]}
    return {"error": "Summary not found"}

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
    ics_path = os.path.join(os.path.dirname(__file__), "agents", "agent-calendar", "local_event.ics")
    if not os.path.exists(ics_path):
        sync_calendar.invoke({})
    
    from icalendar import Calendar
    try:
        with open(ics_path, 'rb') as f:
            gcal = Calendar.from_ical(f.read())
            events = []
            for component in gcal.walk():
                if component.name == "VEVENT":
                    start = component.get('dtstart').dt
                    end = component.get('dtend').dt
                    
                    start_str = start.isoformat() if hasattr(start, 'isoformat') else str(start)
                    end_str = end.isoformat() if hasattr(end, 'isoformat') else str(end)

                    events.append({
                        "summary": str(component.get('summary')),
                        "start": start_str,
                        "end": end_str,
                        "location": str(component.get('location', 'N/A'))
                    })
            return sorted(events, key=lambda x: x['start'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/calendar/add")
async def api_add_event(event: EventCreate):
    try:
        res = add_event.invoke({
            "summary": event.summary,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "location": event.location
        })
        return {"status": "success", "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/calendar/remove")
async def api_remove_event(event: EventRemove):
    try:
        # L'outil remove_event a été corrigé pour être plus robuste sur les dates
        res = remove_event.invoke({
            "summary": event.summary,
            "start_time": event.start_time
        })
        return {"status": "removed", "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve the static React build if it exists
if os.path.exists("campus-os/build"):
    app.mount("/", StaticFiles(directory="campus-os/build", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Lancement de Speech Interface avec API Calendrier...")
    uvicorn.run(app, host="0.0.0.0", port=8000)