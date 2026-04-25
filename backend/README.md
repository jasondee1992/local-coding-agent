# Backend

This backend provides the current safe local backend for the Local Coding Agent: a FastAPI service that proxies chat requests to a local Ollama model and includes read-only repository inspection utilities for future agent context building.

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

## Read-only repo utilities

The backend also includes internal Phase 2 utilities under `app.repo` for:

- filtering files to approved text and code types
- scanning a project directory without leaving the project root
- skipping ignored directories and oversized files
- building markdown summaries and file-context bundles

These utilities are read-only and do not perform file mutation, shell execution, or git commands.

Scan:

```bash
curl -X POST http://127.0.0.1:8000/repo/scan \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/home/udot/PROJECTS/local-coding-agent","max_files":50}'
```

Summary:

```bash
curl -X POST http://127.0.0.1:8000/repo/summary \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/home/udot/PROJECTS/local-coding-agent","max_files":50}'
```

Ask:

```bash
curl -X POST http://127.0.0.1:8000/repo/ask \
  -H "Content-Type: application/json" \
  -d '{
    "project_path":"/home/udot/PROJECTS/local-coding-agent",
    "question":"Which files define repo scanning and safe file reads?",
    "files":["backend/app/repo/repo_reader.py","backend/app/repo/context_builder.py"]
  }'
```
