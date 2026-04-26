from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

from app.config import get_settings

IGNORED_DIR_NAMES = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".idea",
    ".vscode",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
}

IGNORED_FILE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".exe",
    ".dll",
    ".so",
    ".pyc",
    ".sqlite",
    ".db",
    ".env",
}

ALLOWED_FILE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".md",
    ".txt",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".css",
    ".scss",
    ".html",
    ".sql",
    ".sh",
    ".ps1",
}


class WorkspaceReaderError(ValueError):
    """Raised when workspace access violates client-agent safety rules."""


def resolve_project_root(project_path: str) -> Path:
    cleaned = project_path.strip()
    if not cleaned:
        raise WorkspaceReaderError("project_path must not be empty.")
    project_root = Path(cleaned).resolve()
    if not project_root.exists():
        raise WorkspaceReaderError("project_path does not exist.")
    if not project_root.is_dir():
        raise WorkspaceReaderError("project_path must be a directory.")
    return project_root


def _normalize_relative_path(relative_path: str) -> str:
    cleaned = relative_path.strip()
    if not cleaned:
        raise WorkspaceReaderError("relative_path must not be empty.")
    if cleaned.startswith(("/", "\\")) or "\\" in cleaned:
        raise WorkspaceReaderError("relative_path must be a safe project-relative path.")
    normalized = PurePosixPath(cleaned)
    if any(part in {"", ".", ".."} for part in normalized.parts):
        raise WorkspaceReaderError("relative_path contains unsafe path segments.")
    return normalized.as_posix()


def _resolve_target_path(project_root: Path, relative_path: str) -> tuple[str, Path]:
    normalized = _normalize_relative_path(relative_path)
    target_path = (project_root / normalized).resolve()
    if project_root not in {target_path, *target_path.parents}:
        raise WorkspaceReaderError("Resolved path escapes project_path.")
    return normalized, target_path


def _is_allowed_file(path: Path) -> bool:
    lowered_name = path.name.lower()
    suffixes = {suffix.lower() for suffix in path.suffixes}
    if any(suffix in IGNORED_FILE_SUFFIXES for suffix in suffixes):
        return False
    return path.suffix.lower() in ALLOWED_FILE_EXTENSIONS


def _max_size_bytes() -> int:
    return get_settings().client_max_file_size_kb * 1024


def scan_workspace(project_path: str, max_files: int = 300) -> list[dict]:
    project_root = resolve_project_root(project_path)
    files: list[dict] = []

    for current_root, dir_names, file_names in os.walk(project_root):
        dir_names[:] = [
            name for name in sorted(dir_names)
            if name.lower() not in IGNORED_DIR_NAMES
        ]
        current_path = Path(current_root)
        for file_name in sorted(file_names):
            candidate = current_path / file_name
            if not _is_allowed_file(candidate):
                continue
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if project_root not in {resolved, *resolved.parents}:
                continue
            try:
                stat = resolved.stat()
            except OSError:
                continue
            relative = resolved.relative_to(project_root).as_posix()
            files.append(
                {
                    "path": relative,
                    "size_bytes": stat.st_size,
                    "extension": resolved.suffix.lower(),
                }
            )
            if len(files) >= max_files:
                return files

    return files


def read_workspace_file(project_path: str, relative_path: str) -> str:
    project_root = resolve_project_root(project_path)
    normalized, target_path = _resolve_target_path(project_root, relative_path)
    if not target_path.is_file():
        raise WorkspaceReaderError(f"Target file does not exist: {normalized}")
    if not _is_allowed_file(target_path):
        raise WorkspaceReaderError(f"File type is not allowed: {normalized}")
    try:
        size_bytes = target_path.stat().st_size
    except OSError as exc:
        raise WorkspaceReaderError(f"Unable to read file metadata: {normalized}") from exc
    if size_bytes > _max_size_bytes():
        raise WorkspaceReaderError(f"File exceeds max size limit: {normalized}")
    return target_path.read_text(encoding="utf-8", errors="replace")


def build_context_files(project_path: str, files: list[str]) -> list[dict]:
    context_files: list[dict] = []
    seen: set[str] = set()
    for relative_path in files:
        normalized = _normalize_relative_path(relative_path)
        if normalized in seen:
            continue
        seen.add(normalized)
        context_files.append(
            {
                "path": normalized,
                "content": read_workspace_file(project_path, normalized),
            }
        )
    return context_files
