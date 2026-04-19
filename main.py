# main.py
import asyncio
import json
import logging
import os
import warnings
warnings.filterwarnings("ignore")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from orchestrator import run_orchestrator, run_agents_async, decide_agents, synthesize_stream, chat_directly_stream, get_student_context

app = FastAPI(title="Campus Co-Pilot API")


@app.on_event("startup")
async def warmup():
    """Pre-warm Cognee embeddings model so first user request is fast."""
    try:
        from cognee_memory import get_student_context
        await get_student_context("warmup")
        print("✅ Cognee pré-chargé — prêt pour la démo")
    except Exception as e:
        print(f"⚠️ Warmup Cognee échoué ({e}) — première requête sera lente")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    agents_called: list   # pour le frontend (afficher les icônes actives)
    status_events: list = []  # progression des agents pour le frontend


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    result = await run_orchestrator(req.message, session_id=req.session_id)
    return ChatResponse(
        response=result["response"],
        agents_called=result["agents_called"],
        status_events=result.get("status_events", []),
    )


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    async def event_generator():
        memory_context, agents = await asyncio.gather(
            get_student_context(req.message),
            decide_agents(req.message, req.session_id),
        )

        if agents:
            results, status_events = await run_agents_async(agents, req.message, req.session_id)
            for ev in status_events:
                yield f"data: {json.dumps({'type': 'status', **ev})}\n\n"
            async for chunk in synthesize_stream(results, memory_context, req.message, req.session_id):
                yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
        else:
            async for chunk in chat_directly_stream(req.message, memory_context, req.session_id):
                yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'agents': agents})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.delete("/chat/history")
async def clear_history(session_id: str = "default"):
    """Remet la conversation à zéro."""
    from orchestrator import clear_conversation
    clear_conversation(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.get("/memory")
async def memory():
    """Retourne l'état de la mémoire Cognee (utile pour la démo)."""
    from cognee_memory import get_memory_summary
    return get_memory_summary()
