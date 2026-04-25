from pathlib import Path

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

IGNORED_FILE_NAMES = {".env"}


def is_ignored_dir(name: str) -> bool:
    return name.strip().lower() in IGNORED_DIR_NAMES


def is_ignored_file(name: str) -> bool:
    lowered_name = Path(name).name.lower()
    suffixes = [suffix.lower() for suffix in Path(lowered_name).suffixes]
    return lowered_name in IGNORED_FILE_NAMES or any(
        suffix in IGNORED_FILE_SUFFIXES for suffix in suffixes
    )


def is_allowed_file(name: str) -> bool:
    lowered_name = Path(name).name.lower()
    extension = Path(lowered_name).suffix.lower()
    return not is_ignored_file(lowered_name) and extension in ALLOWED_FILE_EXTENSIONS
