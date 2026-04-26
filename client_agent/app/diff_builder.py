from __future__ import annotations

import difflib
import re

from app.workspace_reader import read_workspace_file


def _strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    fenced_match = re.fullmatch(r"```(?:[A-Za-z0-9_+-]+)?\s*(.*?)```", stripped, flags=re.DOTALL)
    if fenced_match:
        return fenced_match.group(1).strip()
    return stripped


def normalize_anchor(anchor: str, task: str = "") -> str:
    cleaned = _strip_markdown_fences(anchor)
    lowered_anchor = cleaned.lower()
    lowered_task = task.lower()
    if "/health" in lowered_anchor or "def health" in lowered_anchor:
        return "health"
    if "/health" in lowered_task and "after health" in lowered_task:
        return "health"
    return cleaned


def _normalize_inserted_code(code: str) -> str:
    return _strip_markdown_fences(code).strip()


def _find_function_end(lines: list[str], start_index: int) -> int:
    base_indent = len(lines[start_index]) - len(lines[start_index].lstrip(" "))
    index = start_index + 1
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        current_indent = len(line) - len(line.lstrip(" "))
        if stripped and current_indent <= base_indent:
            break
        index += 1
    return index


def _format_inserted_block(original: str, insert_at: int, code: str) -> str:
    before = original[:insert_at]
    after = original[insert_at:]
    code_block = _normalize_inserted_code(code)
    if not code_block:
        return original

    before_newlines = len(before) - len(before.rstrip("\n"))
    after_newlines = len(after) - len(after.lstrip("\n"))
    before_padding = "\n" * max(0, 2 - before_newlines)
    after_padding = "\n" * max(0, 1 - after_newlines)
    return before + before_padding + code_block + after_padding + after


def _find_health_insert_offset(lines: list[str]) -> int | None:
    route_index: int | None = None
    for index, line in enumerate(lines):
        if '@app.get("/health")' in line or '@router.get("/health")' in line:
            route_index = index
            break
    if route_index is None:
        return None

    function_index: int | None = None
    for index in range(route_index + 1, len(lines)):
        stripped = lines[index].lstrip()
        if stripped.startswith("async def health(") or stripped.startswith("def health("):
            function_index = index
            break
        if stripped.startswith("@") and index > route_index + 1:
            break
    if function_index is None:
        return None

    end_index = _find_function_end(lines, function_index)
    return sum(len(line) for line in lines[:end_index])


def _find_anchor_insert_offset(original: str, normalized_anchor: str) -> int | None:
    lines = original.splitlines(keepends=True)
    if normalized_anchor == "health":
        return _find_health_insert_offset(lines)

    for index, line in enumerate(lines):
        if normalized_anchor in line:
            return sum(len(current_line) for current_line in lines[: index + 1])
    return None


def generate_insert_after_anchor_diff(
    project_path: str,
    target_file: str,
    anchor: str,
    code: str,
    task: str = "",
) -> dict:
    original = read_workspace_file(project_path, target_file)
    normalized_anchor = normalize_anchor(anchor, task=task)
    warnings: list[str] = []
    normalized_code = _normalize_inserted_code(code)
    if not normalized_code:
        warnings.append("No insertable code was provided.")
        return {
            "generated_diff": "",
            "warnings": warnings,
            "normalized_anchor": normalized_anchor,
        }

    insert_offset = _find_anchor_insert_offset(original, normalized_anchor)
    if insert_offset is None:
        warnings.append(f"Anchor not found in target file: {normalized_anchor}")
        return {
            "generated_diff": "",
            "warnings": warnings,
            "normalized_anchor": normalized_anchor,
        }

    updated = _format_inserted_block(original, insert_offset, normalized_code)
    diff_lines = difflib.unified_diff(
        original.splitlines(),
        updated.splitlines(),
        fromfile=f"a/{target_file}",
        tofile=f"b/{target_file}",
        lineterm="",
    )
    return {
        "generated_diff": "\n".join(diff_lines),
        "warnings": warnings,
        "normalized_anchor": normalized_anchor,
    }


def validate_plan(
    task: str,
    target_file: str,
    operation: str,
    code: str,
    requested_files: list[str],
) -> list[str]:
    warnings: list[str] = []
    lowered_task = task.lower()
    lowered_code = code.lower()

    if target_file not in requested_files:
        warnings.append("Planner selected a target file that was not explicitly requested.")
    if operation != "insert_after_anchor":
        warnings.append("Planner returned an unsupported operation.")
    if "no response_model" in lowered_task and "response_model" in lowered_code:
        warnings.append("Task says no response_model, but the generated code includes response_model.")
    if ("no schema" in lowered_task or "import schema" in lowered_task) and (
        "app.schemas" in code or "from app.schemas" in code
    ):
        warnings.append("Task restricts schema usage, but the generated code references app.schemas.")
    if "/version" in task and (
        '@app.get("/version")' not in code and '@router.get("/version")' not in code
    ):
        warnings.append('Task mentions /version, but the generated code does not add `@app.get("/version")`.')
    if any(marker in code for marker in ("--- ", "+++ ", "@@ ")):
        warnings.append("Generated code appears to contain unified diff markers instead of raw insertion code.")
    return warnings
