# Local Coding Agent

Local Coding Agent is an on-prem AI coding agent project designed to run against a local LLM through Ollama. Phase 2.5 keeps the backend safe and local-first: it can chat with the model, inspect a repository in read-only mode, and exposes a few operational endpoints to make local Ollama use faster and easier to debug.

## Phase 2.5 scope

- FastAPI backend
- `GET /health` for service configuration status
- `GET /settings` for non-secret runtime settings
- `GET /models` for installed Ollama models
- `POST /warmup` to warm the configured model
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

`OLLAMA_NUM_PREDICT` can be lowered in `backend/.env` if you want faster, shorter answers from the local model.

## Run the backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

The backend defaults to `http://127.0.0.1:8000`.

The first local LLM request can be slower because Ollama may need to load the model into memory. Use `/warmup` to reduce that startup hit before interactive use.

## Test the health endpoint

```bash
curl http://127.0.0.1:8000/health
```

## Test the settings endpoint

```bash
curl http://127.0.0.1:8000/settings
```

## Test the models endpoint

```bash
curl http://127.0.0.1:8000/models
```

## Warm up the local model

```bash
curl -X POST http://127.0.0.1:8000/warmup
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

## Propose a patch without applying it

```bash
curl -X POST http://127.0.0.1:8000/repo/propose \
  -H "Content-Type: application/json" \
  -d '{
    "project_path":"/home/udot/PROJECTS/local-coding-agent",
    "task":"Add a short docstring to the Ollama client helper functions.",
    "files":["backend/app/llm/ollama_client.py"]
  }'
```

## Plan and optionally save a change proposal

```bash
curl -X POST http://127.0.0.1:8000/repo/plan-change \
  -H "Content-Type: application/json" \
  -d '{
    "project_path":"/home/udot/PROJECTS/local-coding-agent",
    "task":"Add a simple /version endpoint after health that returns a plain dictionary using existing settings values.",
    "files":["backend/app/main.py"],
    "save_proposal":true,
    "proposal_name":"version-endpoint"
  }'
```

## List saved proposals

```bash
curl http://127.0.0.1:8000/repo/proposals
```

## Read one saved proposal

```bash
curl http://127.0.0.1:8000/repo/proposals/<proposal_id>
```

## Notes

- Ollama must be running locally before calling `/chat`.
- Ollama must be running locally before calling `/models` or `/warmup`.
- Ollama must also be running locally before calling `/repo/ask`.
- Ollama must also be running locally before calling `/repo/propose`.
- The backend reads configuration from `backend/.env`.
- Repository utilities only allow approved text and code files, enforce path boundaries, and skip oversized files.
- `OLLAMA_KEEP_ALIVE` helps keep the model loaded between requests.
- `OLLAMA_NUM_PREDICT` is the main knob for shortening responses and improving local latency.
- `/repo/propose` returns text only and does not apply or write any patch.
- `/repo/propose` may also return proposal warnings when a suggested patch looks incomplete or suspicious.
- The proposal validator checks for incomplete imports, suspicious added command lines, endpoint tasks that do not appear to add the requested route, explicit constraints such as `do not use response_model` or `plain dictionary only`, and some unnecessary imports or client instantiations.
- `/repo/plan-change` can optionally save proposal JSON and patch files under the local `proposals/` directory without modifying the target project files.
- Proposal warnings are advisory only and do not mean any files were changed.
- File mutation and execution features remain intentionally out of scope.
