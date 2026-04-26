from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.workspace_reader import WorkspaceReaderError, resolve_project_root


class AuthorizationError(PermissionError):
    """Raised when a workspace action is attempted without local approval."""


def _client_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _authorizations_dir() -> Path:
    return _client_root() / "authorizations"


def _safe_authorization_id(value: str) -> str:
    if "/" in value or "\\" in value or ".." in value:
        raise ValueError("Invalid authorization_id")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
        raise ValueError("Invalid authorization_id")
    return value


def _authorization_id_for_project(project_path: str) -> tuple[str, str]:
    resolved_project_path = str(resolve_project_root(project_path))
    digest = hashlib.sha256(resolved_project_path.encode("utf-8")).hexdigest()
    return digest[:16], resolved_project_path


def _normalize_permissions(payload: dict[str, Any] | None) -> dict[str, bool]:
    payload = payload or {}
    return {
        "read_files": bool(payload.get("read_files", False)),
        "create_files": bool(payload.get("create_files", False)),
        "modify_files": bool(payload.get("modify_files", False)),
        "apply_changes": bool(payload.get("apply_changes", False)),
        "delete_files": bool(payload.get("delete_files", False)),
    }


def _task_mentions_creation(task: str) -> bool:
    lowered = task.lower()
    phrases = ("create", "new file", "new page", "hello world", "html", "css", "javascript")
    return any(phrase in lowered for phrase in phrases)


def preview_project_authorization(project_path: str, task: str = "", files: list[str] | None = None) -> dict[str, Any]:
    authorization_id, resolved_project_path = _authorization_id_for_project(project_path)
    existing = None
    try:
        existing = load_project_authorization(authorization_id)
    except FileNotFoundError:
        existing = None

    has_files = any(path.strip() for path in (files or []))
    questions = [
        {
            "permission": "read_files",
            "question": f"Allow the agent to read approved files inside {resolved_project_path}?",
            "recommended": True,
            "reason": "Required for scan and plan requests.",
        },
        {
            "permission": "create_files",
            "question": f"Allow the agent to create new files inside {resolved_project_path}?",
            "recommended": _task_mentions_creation(task),
            "reason": "Needed for tasks that add new HTML, CSS, or JavaScript files.",
        },
        {
            "permission": "modify_files",
            "question": f"Allow the agent to modify existing files inside {resolved_project_path}?",
            "recommended": has_files,
            "reason": "Needed to apply diffs to existing files.",
        },
        {
            "permission": "apply_changes",
            "question": f"Allow the agent to apply saved proposals inside {resolved_project_path} after explicit confirm?",
            "recommended": False,
            "reason": "Keeps plan generation and file writes separate.",
        },
        {
            "permission": "delete_files",
            "question": f"Allow the agent to delete files inside {resolved_project_path}?",
            "recommended": False,
            "reason": "Deletion remains disabled by default and is not currently implemented.",
        },
    ]
    return {
        "authorization_id": authorization_id,
        "project_path": resolved_project_path,
        "has_existing_authorization": existing is not None,
        "current_permissions": _normalize_permissions(existing.get("permissions")) if existing else None,
        "questions": questions,
    }


def save_project_authorization(
    project_path: str,
    *,
    read_files: bool,
    create_files: bool,
    modify_files: bool,
    apply_changes: bool,
    delete_files: bool = False,
) -> dict[str, Any]:
    authorization_id, resolved_project_path = _authorization_id_for_project(project_path)
    authorizations_dir = _authorizations_dir()
    authorizations_dir.mkdir(parents=True, exist_ok=True)
    authorization_path = authorizations_dir / f"{authorization_id}.json"
    existing = None
    if authorization_path.is_file():
        existing = json.loads(authorization_path.read_text(encoding="utf-8"))

    now = datetime.now(UTC).isoformat()
    payload = {
        "authorization_id": authorization_id,
        "project_path": resolved_project_path,
        "created_at": existing.get("created_at") if existing else now,
        "updated_at": now,
        "permissions": {
            "read_files": read_files,
            "create_files": create_files,
            "modify_files": modify_files,
            "apply_changes": apply_changes,
            "delete_files": delete_files,
        },
    }
    authorization_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def list_project_authorizations() -> list[dict[str, Any]]:
    authorizations_dir = _authorizations_dir()
    if not authorizations_dir.exists():
        return []

    items: list[dict[str, Any]] = []
    for auth_file in sorted(authorizations_dir.glob("*.json")):
        try:
            data = json.loads(auth_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        permissions = _normalize_permissions(data.get("permissions"))
        items.append(
            {
                "authorization_id": data.get("authorization_id") or auth_file.stem,
                "project_path": data.get("project_path"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "permissions": permissions,
            }
        )
    return items


def load_project_authorization(authorization_id: str) -> dict[str, Any]:
    safe_id = _safe_authorization_id(authorization_id)
    authorization_path = _authorizations_dir() / f"{safe_id}.json"
    if not authorization_path.is_file():
        raise FileNotFoundError(safe_id)
    return json.loads(authorization_path.read_text(encoding="utf-8"))


def require_project_authorization(
    project_path: str,
    *,
    read_files: bool = False,
    create_files: bool = False,
    modify_files: bool = False,
    apply_changes: bool = False,
    delete_files: bool = False,
) -> dict[str, Any]:
    try:
        preview = preview_project_authorization(project_path)
    except WorkspaceReaderError as exc:
        raise AuthorizationError(str(exc)) from exc

    if not preview["has_existing_authorization"]:
        raise AuthorizationError(
            "Project path is not authorized. Call /workspace/authorize/preview and /workspace/authorize first."
        )

    authorization = load_project_authorization(preview["authorization_id"])
    permissions = _normalize_permissions(authorization.get("permissions"))
    missing: list[str] = []
    required = {
        "read_files": read_files,
        "create_files": create_files,
        "modify_files": modify_files,
        "apply_changes": apply_changes,
        "delete_files": delete_files,
    }
    for permission_name, required_value in required.items():
        if required_value and not permissions.get(permission_name, False):
            missing.append(permission_name)
    if missing:
        raise AuthorizationError(
            "Project path is authorized, but missing required permissions: " + ", ".join(sorted(missing))
        )
    return authorization
