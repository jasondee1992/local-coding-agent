# client_agent

`client_agent` is the local workspace agent that runs on the machine that owns the project files. It reads selected local files, sends only that selected context to the Linux AI server, generates unified diffs locally, saves proposals locally, and applies proposals locally only after explicit confirmation.

The Linux AI server runs Ollama and exposes `POST /ai/plan-from-context`. A browser connecting to the backend over IP cannot grant the Linux server direct access to files on another laptop or PC, so `client_agent` fills that gap.

## Configuration

Copy `.env.example` to `.env` and set `AI_SERVER_BASE_URL` to the Linux AI server.

Linux example:

```env
AI_SERVER_BASE_URL=http://192.168.110.50:8000
```

Windows path JSON example:

```json
"C:\\Users\\Jason\\Projects\\payroll-frontend"
```

## Setup

```bash
cd client_agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run

```bash
cd client_agent
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload
```

## Example curl

Check client and AI server status:

```bash
curl http://127.0.0.1:8100/status
```

Scan a local workspace:

```bash
curl -X POST http://127.0.0.1:8100/workspace/scan \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/home/udot/PROJECTS/local-coding-agent","max_files":50}'
```

Preview the permission questions for a project path:

```bash
curl -X POST http://127.0.0.1:8100/workspace/authorize/preview \
  -H "Content-Type: application/json" \
  -d '{
    "project_path":"/home/udot/PROJECTS/local-coding-agent",
    "task":"Create a simple hello world page with HTML, CSS, and JavaScript.",
    "files":["backend/app/main.py"]
  }'
```

Approve local access for that project path:

```bash
curl -X POST http://127.0.0.1:8100/workspace/authorize \
  -H "Content-Type: application/json" \
  -d '{
    "project_path":"/home/udot/PROJECTS/local-coding-agent",
    "confirm":true,
    "read_files":true,
    "create_files":true,
    "modify_files":true,
    "apply_changes":true,
    "delete_files":false
  }'
```

Plan a local change without modifying files:

```bash
curl -X POST http://127.0.0.1:8100/workspace/plan-change \
  -H "Content-Type: application/json" \
  -d '{
    "project_path":"/home/udot/PROJECTS/local-coding-agent",
    "task":"Add a simple /version endpoint after health that returns a plain dictionary using existing settings values.",
    "files":["backend/app/main.py"],
    "save_proposal":true,
    "proposal_name":"version-endpoint"
  }'
```

List saved proposals:

```bash
curl http://127.0.0.1:8100/workspace/proposals
```

Apply one proposal locally:

```bash
curl -X POST http://127.0.0.1:8100/workspace/proposals/<proposal_id>/apply \
  -H "Content-Type: application/json" \
  -d '{"confirm_apply":true,"allow_warnings":false,"create_backup":true}'
```

## Notes

- `client_agent` never runs shell commands from the API.
- `client_agent` never runs git commands from the API.
- Project access is denied until the client explicitly authorizes the exact `project_path`.
- `/workspace/authorize/preview` returns the permission questions; `/workspace/authorize` stores the answers locally.
- `/workspace/plan-change` does not modify project files.
- Proposals are saved under `client_agent/proposals/`.
- Project authorizations are saved under `client_agent/authorizations/`.
- Backups for applied proposals are saved under `client_agent/proposals/backups/`.
