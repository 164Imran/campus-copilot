# Campus Co-Pilot

An autonomous AI agent built for TUM (Technical University of Munich) students. Developed at the TUM.ai Makeathon 2026. Combines a FastAPI backend with AWS Bedrock (Claude 3.5 Sonnet) and a React frontend styled as a macOS-inspired desktop environment.

## Architecture

```
Frontend (React + TypeScript)
        ↕  REST / WebSocket
Backend (FastAPI)
        ↕
AWS Bedrock — Claude 3.5 Sonnet (orchestrator)
        ↕
Cognee (SQLite + FastEmbed) — memory and RAG
        ↕
Deepgram (live STT) / ElevenLabs (streaming TTS)
```

The orchestrator routes each user request to one or more specialized agents:

| Agent | Responsibility |
|-------|---------------|
| Moodle Agent | Retrieves and summarizes lecture slides and course documents |
| Agenda Agent | Tracks deadlines, exams, and scheduled events |
| Room Agent | Handles study room reservations |

## Interfaces

- **Text chat** — conversational interface with full agent routing
- **Voice** — real-time voice-to-voice via Deepgram (STT) and ElevenLabs (TTS), with karaoke-style word highlighting

## Requirements

- Python 3.11+
- Node.js and npm
- AWS credentials with Bedrock access
- Deepgram API key
- ElevenLabs API key

## Setup

### Backend

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```env
AWS_DEFAULT_REGION=us-east-1
BEDROCK_MODEL_ID=eu.anthropic.claude-sonnet-4-5-20250929-v1:0
DEEPGRAM_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
ELEVENLABS_VOICE_ID=your_voice_id
```

Start the server:

```bash
python speech_interface.py
```

Server runs at `http://localhost:8000`.

### Frontend

```bash
cd campus-os
npm install
npm start
```

Frontend available at `http://localhost:3000`.
