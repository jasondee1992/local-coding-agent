# Local Coding Agent

Local Coding Agent is an on-prem AI coding agent project designed to run against a local LLM through Ollama. Phase 1 delivers only the backend foundation: a safe FastAPI service that can send a user message to the local model and return the model response.

## Phase 1 scope

- FastAPI backend only
- `GET /health` for service configuration status
- `POST /chat` for local model chat
- No repository reading
- No file modification
- No shell execution
- No frontend

## Prerequisites

- Python 3.11+
- Ollama installed and running locally
- The `qwen2.5-coder:7b` model available in Ollama, or an alternative model configured in `.env`

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run the backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

The backend defaults to `http://127.0.0.1:8000`.

## Test the health endpoint

```bash
curl http://127.0.0.1:8000/health
```

Expected shape:

```json
{
  "status": "ok",
  "app": "Local Coding Agent",
  "env": "development",
  "model": "qwen2.5-coder:7b"
}
```

## Test chat with curl

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Explain Python async in two sentences."}'
```

Expected shape:

```json
{
  "response": "..."
}
```

## Notes

- Ollama must be running locally before calling `/chat`.
- The backend reads configuration from `backend/.env`.
- Phase 2 will add broader agent capabilities, but those are intentionally excluded from this version.
