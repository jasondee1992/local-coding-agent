# Local Coding Agent

Local Coding Agent is an on-prem AI coding agent project designed to run against a local LLM through Ollama. Phase 2 keeps the backend safe and local-first: it can chat with the model and includes a read-only repository reader for building future coding context.

## Phase 2 scope

- FastAPI backend
- `GET /health` for service configuration status
- `POST /chat` for local model chat
- Read-only repository scanning and safe file reads
- No file modification
- No shell execution
- No git execution
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

## Scan a repository

```bash
curl -X POST http://127.0.0.1:8000/repo/scan \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/home/udot/PROJECTS/local-coding-agent","max_files":50}'
```

## Build a repository summary

```bash
curl -X POST http://127.0.0.1:8000/repo/summary \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/home/udot/PROJECTS/local-coding-agent","max_files":50}'
```

## Ask a repository question

```bash
curl -X POST http://127.0.0.1:8000/repo/ask \
  -H "Content-Type: application/json" \
  -d '{
    "project_path":"/home/udot/PROJECTS/local-coding-agent",
    "question":"How is Ollama wired into the backend?",
    "files":["backend/app/main.py","backend/app/llm/ollama_client.py"]
  }'
```

## Notes

- Ollama must be running locally before calling `/chat`.
- Ollama must also be running locally before calling `/repo/ask`.
- The backend reads configuration from `backend/.env`.
- Repository utilities only allow approved text and code files, enforce path boundaries, and skip oversized files.
- File mutation and execution features remain intentionally out of scope.
