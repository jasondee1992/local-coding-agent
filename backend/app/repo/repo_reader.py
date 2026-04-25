from dataclasses import dataclass
from pathlib import Path
import os

from app.config import get_settings
from app.repo.file_filters import is_allowed_file, is_ignored_dir, is_ignored_file


class RepoReaderError(ValueError):
    """Raised when a repository path or file request is invalid."""


@dataclass(frozen=True, slots=True)
class RepoFileInfo:
    relative_path: str
    size: int
    extension: str


def _max_file_size_bytes(max_file_size_kb: int | None) -> int:
    settings = get_settings()
    configured_kb = settings.max_file_size_kb if max_file_size_kb is None else max_file_size_kb
    return configured_kb * 1024


def _resolve_project_root(project_path: str) -> Path:
    root = Path(project_path).expanduser().resolve()
    if not root.exists():
        raise RepoReaderError(f"Project path does not exist: {project_path}")
    if not root.is_dir():
        raise RepoReaderError(f"Project path is not a directory: {project_path}")
    return root


def _ensure_within_root(root: Path, candidate: Path) -> Path:
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise RepoReaderError("Requested path escapes the project directory.") from exc
    return resolved


def scan_files(
    project_path: str,
    max_files: int = 300,
    max_file_size_kb: int | None = None,
) -> list[RepoFileInfo]:
    if max_files <= 0:
        raise RepoReaderError("max_files must be greater than zero.")

    root = _resolve_project_root(project_path)
    max_bytes = _max_file_size_bytes(max_file_size_kb)
    files: list[RepoFileInfo] = []

    for current_root, dir_names, file_names in os.walk(root, topdown=True, followlinks=False):
        dir_names[:] = sorted(name for name in dir_names if not is_ignored_dir(name))

        for file_name in sorted(file_names):
            if is_ignored_file(file_name) or not is_allowed_file(file_name):
                continue

            file_path = _ensure_within_root(root, Path(current_root) / file_name)
            try:
                size = file_path.stat().st_size
            except OSError:
                continue

            if size > max_bytes:
                continue

            relative_path = file_path.relative_to(root).as_posix()
            files.append(
                RepoFileInfo(
                    relative_path=relative_path,
                    size=size,
                    extension=file_path.suffix.lower(),
                )
            )

            if len(files) >= max_files:
                return files

    return files


def scan_repo(
    project_path: str,
    max_files: int = 300,
    max_file_size_kb: int | None = None,
) -> list[RepoFileInfo]:
    return scan_files(
        project_path=project_path,
        max_files=max_files,
        max_file_size_kb=max_file_size_kb,
    )


def read_file(
    project_path: str,
    relative_path: str,
    max_file_size_kb: int | None = None,
) -> str:
    if not relative_path.strip():
        raise RepoReaderError("relative_path must not be empty.")

    root = _resolve_project_root(project_path)
    candidate = _ensure_within_root(root, root / relative_path)

    if not candidate.exists():
        raise RepoReaderError(f"File does not exist: {relative_path}")
    if not candidate.is_file():
        raise RepoReaderError(f"Path is not a file: {relative_path}")
    if is_ignored_file(candidate.name) or not is_allowed_file(candidate.name):
        raise RepoReaderError(f"File type is not allowed: {relative_path}")

    max_bytes = _max_file_size_bytes(max_file_size_kb)
    try:
        size = candidate.stat().st_size
    except OSError as exc:
        raise RepoReaderError(f"Unable to read file metadata: {relative_path}") from exc

    if size > max_bytes:
        raise RepoReaderError(
            f"File exceeds max size limit of {max_bytes // 1024} KB: {relative_path}"
        )

    try:
        return candidate.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise RepoReaderError(f"Unable to read file: {relative_path}") from exc
