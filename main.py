# main.py
import logging
import os
import warnings
warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv()

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from orchestrator import run_orchestrator

API_KEY = os.getenv("API_KEY")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]


def require_api_key(x_api_key: str = Header(None)):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


app = FastAPI(title="Campus Co-Pilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
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


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key)])
async def chat(req: ChatRequest):
    result = await run_orchestrator(req.message, session_id=req.session_id)
    return ChatResponse(
        response=result["response"],
        agents_called=result["agents_called"],
        status_events=result.get("status_events", []),
    )


@app.delete("/chat/history", dependencies=[Depends(require_api_key)])
async def clear_history(session_id: str = "default"):
    """Remet la conversation à zéro."""
    from orchestrator import clear_conversation
    clear_conversation(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.get("/memory", dependencies=[Depends(require_api_key)])
async def memory():
    """Retourne l'état de la mémoire Cognee (utile pour la démo)."""
    from cognee_memory import get_memory_summary
    return get_memory_summary()


class RagAnswerRequest(BaseModel):
    question: str
    course: str


class RagCompareRequest(BaseModel):
    topic: str
    course1: str
    course2: str


@app.post("/rag/answer", dependencies=[Depends(require_api_key)])
async def rag_answer(req: RagAnswerRequest):
    """Q&A sur un cours via les vecteurs RAG (S3 Vectors + Bedrock)."""
    from aws.rag_builder import answer_question
    try:
        return {"answer": answer_question(req.question, req.course)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@app.post("/rag/compare", dependencies=[Depends(require_api_key)])
async def rag_compare(req: RagCompareRequest):
    """Analyse croisée d'un thème entre deux cours."""
    from aws.rag_builder import compare_courses
    try:
        return {"analysis": compare_courses(req.topic, req.course1, req.course2)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
