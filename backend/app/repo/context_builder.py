from collections import defaultdict
from pathlib import Path

from app.repo.repo_reader import read_file, scan_files

IMPORTANT_PATHS = [
    "README.md",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "app/main.py",
    "src/",
    "backend/",
    "frontend/",
]


def build_repo_overview(project_path: str, max_files: int = 300) -> str:
    files = scan_files(project_path=project_path, max_files=max_files)
    grouped_paths: dict[str, list[str]] = defaultdict(list)
    file_paths = [file_info.relative_path for file_info in files]
    path_set = set(file_paths)

    for relative_path in file_paths:
        top_level = relative_path.split("/", 1)[0] if "/" in relative_path else "(root)"
        grouped_paths[top_level].append(relative_path)

    important_paths: list[str] = []
    for candidate in IMPORTANT_PATHS:
        if candidate.endswith("/"):
            prefix = candidate
            if any(path.startswith(prefix) for path in file_paths):
                important_paths.append(candidate)
        elif candidate in path_set:
            important_paths.append(candidate)

    lines = [
        "# Repository Overview",
        "",
        f"- Project path: `{Path(project_path).expanduser().resolve()}`",
        f"- Total included files: {len(files)}",
        "",
        "## Important paths",
    ]

    if important_paths:
        lines.extend(f"- `{path}`" for path in important_paths)
    else:
        lines.append("- None of the tracked important paths were found.")

    lines.extend(["", "## File tree"])

    for group_name in sorted(grouped_paths):
        lines.append(f"### {group_name}")
        lines.extend(f"- `{path}`" for path in grouped_paths[group_name])
        lines.append("")

    if not files:
        lines.append("No allowed files were found within the configured limits.")

    return "\n".join(lines).strip()


def build_context_from_files(project_path: str, relative_paths: list[str]) -> str:
    deduped_paths = list(dict.fromkeys(relative_paths))
    lines = [
        "# Repository Context",
        "",
        f"- Project path: `{Path(project_path).expanduser().resolve()}`",
        f"- Included files: {len(deduped_paths)}",
    ]

    for relative_path in deduped_paths:
        content = read_file(project_path=project_path, relative_path=relative_path)
        lines.extend(
            [
                "",
                f"### File: {relative_path}",
                "```text",
                content,
                "```",
            ]
        )

    return "\n".join(lines).strip()
