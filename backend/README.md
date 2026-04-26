# Backend

This backend provides the current safe local backend for the Local Coding Agent: a FastAPI service that proxies chat requests to a local Ollama model, includes repository inspection utilities, saves proposal artifacts locally, and can conservatively apply a reviewed saved proposal without invoking shell or git.

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

Lower `OLLAMA_NUM_PREDICT` in `.env` if you want shorter and faster local responses.

## Run

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

The API will listen on `http://127.0.0.1:8000` by default.

The first LLM-backed request can be slower because Ollama may need to load the configured model. `POST /warmup` is useful before interactive testing.

## Quick checks

Health:

```bash
curl http://127.0.0.1:8000/health
```

Settings:

```bash
curl http://127.0.0.1:8000/settings
```

Models:

```bash
curl http://127.0.0.1:8000/models
```

Warmup:

```bash
curl -X POST http://127.0.0.1:8000/warmup
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

The repository utilities do not perform shell execution or git commands. Proposal planning is read-only. Proposal apply performs a single validated file write only after explicit confirmation and backup creation.

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

Propose:

```bash
curl -X POST http://127.0.0.1:8000/repo/propose \
  -H "Content-Type: application/json" \
  -d '{
    "project_path":"/home/udot/PROJECTS/local-coding-agent",
    "task":"Propose a minimal refactor for the repo reader error messages.",
    "files":["backend/app/repo/repo_reader.py"]
  }'
```

Plan and save:

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

Saved proposals:

```bash
curl http://127.0.0.1:8000/repo/proposals
curl http://127.0.0.1:8000/repo/proposals/<proposal_id>
```

Apply a saved proposal:

```bash
curl -X POST http://localhost:8000/repo/proposals/<proposal_id>/apply \
  -H "Content-Type: application/json" \
  -d '{"confirm_apply":true,"allow_warnings":false,"create_backup":true}'
```

This writes to the target file, requires explicit `confirm_apply=true`, creates a backup under `proposals/backups/`, and refuses proposals with warnings unless `allow_warnings=true`.

`/repo/propose` is read-only. It returns an explanation, a proposed unified diff, the files used as context, safety notes, and may include warnings when a suggested patch looks incomplete or suspicious. The proposal validator checks for incomplete imports, suspicious added command lines, endpoint tasks that do not appear to add the requested route, explicit constraints such as `do not use response_model` or `plain dictionary only`, and some unnecessary imports or client instantiations. These warnings are advisory only and do not mean any files were changed or applied.

`/repo/plan-change` is read-only. It returns a planner-generated insertion plan plus a Python-generated unified diff, and it can optionally save the resulting proposal to the local `proposals/` directory as a JSON record and `.patch` file.

`/repo/proposals/{proposal_id}/apply` is intentionally conservative. It only applies a saved single-file diff to the saved `target_file`, requires `confirm_apply=true`, creates a backup before writing, rejects path traversal, blocks warnings unless `allow_warnings=true`, and refuses to write when the current file no longer matches the expected pre-apply context.
