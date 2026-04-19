import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
import websockets
from text_speech import generate_audio_bytes
import orchestrator

load_dotenv()
app = FastAPI()

# REMPLACE PAR TA CLÉ DEEPGRAM (Gratiut 200$)
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# L'appel à l'Orchestrateur se fera directement dans la fonction send_to_dg

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
                                # La phrase est finie, on l'affiche mais on attend l'arrêt pour envoyer à Bedrock
                                pass
                except websockets.exceptions.ConnectionClosed:
                    print("Deepgram a fermé la connexion (timeout attendu après la fin de l'audio).")
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
                                        
                                        # Envoyer tout le texte d'un coup au frontend
                                        try:
                                            await websocket.send_json({"type": "agent", "text": full_text})
                                        except Exception:
                                            return
                                            
                                        # Découper en phrases pour le TTS
                                        import re
                                        # On découpe sur la ponctuation (., !, ?, \n, :)
                                        sentences = re.split(r'([.!?\n:])', full_text)
                                        
                                        # Recombiner les phrases avec leur ponctuation
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
                                            
                                        # Générer l'audio phrase par phrase et l'envoyer de façon synchrone
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

                                # Démarrer le traitement en arrière-plan sans bloquer la réception
                                asyncio.create_task(process_orchestrator_and_tts(data["text"]))
                                
                except Exception as e:
                    print(f"Info send_to_dg: {e}")

            await asyncio.gather(receive_from_dg(), send_to_dg())
    except Exception as e:
        print(f"❌ Erreur : {e}")


if __name__ == "__main__":
    import uvicorn
    print("🚀 Tentative de lancement du serveur...")
    uvicorn.run(app, host="0.0.0.0", port=8000)