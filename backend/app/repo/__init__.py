"""Read-only repository inspection utilities."""

from app.repo.change_planner import plan_change
from app.repo.context_builder import build_context_from_files, build_repo_overview
from app.repo.patch_proposer import propose_patch
from app.repo.repo_reader import RepoFileInfo, RepoReaderError, read_file, scan_files, scan_repo

__all__ = [
    "RepoFileInfo",
    "RepoReaderError",
    "build_context_from_files",
    "build_repo_overview",
    "plan_change",
    "propose_patch",
    "read_file",
    "scan_files",
    "scan_repo",
]
