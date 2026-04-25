# Backend

This backend provides Phase 1 of the Local Coding Agent: a minimal FastAPI service that proxies chat requests to a local Ollama model.

## Requirements

- Python 3.11+
- Ollama running on the same machine
- A local model available in Ollama, defaulting to `qwen2.5-coder:7b`

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run

```bash
cd backend
uvicorn app.main:app --reload
```

The API will listen on `http://127.0.0.1:8000` by default.

## Quick checks

Health:

```bash
curl http://127.0.0.1:8000/health
```

Chat:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Write a short Python hello world example."}'
```

If the chat request fails with a service error, confirm that Ollama is running locally and the configured model is available.
