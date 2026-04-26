from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import get_settings


def _client_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _proposals_dir() -> Path:
    return _client_root() / get_settings().client_proposals_dir


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:50] or "proposal"


def _safe_proposal_id(value: str) -> str:
    if "/" in value or "\\" in value or ".." in value:
        raise ValueError("Invalid proposal_id")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
        raise ValueError("Invalid proposal_id")
    return value


def save_client_proposal(
    project_path: str,
    task: str,
    result: dict,
    proposal_name: str | None = None,
) -> dict:
    proposals_dir = _proposals_dir()
    proposals_dir.mkdir(parents=True, exist_ok=True)

    created_at = datetime.now(UTC).isoformat()
    slug_source = proposal_name or result.get("target_file") or task
    proposal_id = f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}-{_slugify(slug_source)}"
    proposal_path = proposals_dir / f"{proposal_id}.json"
    patch_path = proposals_dir / f"{proposal_id}.patch"

    payload = {
        "proposal_id": proposal_id,
        "created_at": created_at,
        "project_path": project_path,
        "task": task,
        "target_file": result.get("target_file"),
        "operation": result.get("operation", ""),
        "anchor": result.get("anchor"),
        "code": result.get("code", ""),
        "generated_diff": result.get("generated_diff", ""),
        "warnings": list(result.get("warnings", [])),
        "safety_notes": list(result.get("safety_notes", [])),
        "ai_server_response": result.get("ai_server_response"),
    }

    proposal_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    patch_path.write_text(result.get("generated_diff", ""), encoding="utf-8")
    return {
        "proposal_id": proposal_id,
        "proposal_path": str(proposal_path),
    }


def list_client_proposals() -> list[dict]:
    proposals_dir = _proposals_dir()
    if not proposals_dir.exists():
        return []

    items: list[dict] = []
    for proposal_file in sorted(proposals_dir.glob("*.json"), reverse=True):
        try:
            data = json.loads(proposal_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        items.append(
            {
                "proposal_id": data.get("proposal_id") or proposal_file.stem,
                "created_at": data.get("created_at"),
                "task": data.get("task"),
                "target_file": data.get("target_file"),
                "warnings_count": len(data.get("warnings", [])),
            }
        )
    return items


def load_client_proposal(proposal_id: str) -> dict[str, Any]:
    safe_id = _safe_proposal_id(proposal_id)
    proposal_path = _proposals_dir() / f"{safe_id}.json"
    if not proposal_path.is_file():
        raise FileNotFoundError(safe_id)
    return json.loads(proposal_path.read_text(encoding="utf-8"))
