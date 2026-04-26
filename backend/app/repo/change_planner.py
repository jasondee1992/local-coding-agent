from __future__ import annotations

import difflib
import re
from pathlib import Path

from app.llm.ollama_client import ask_ollama
from app.repo.context_builder import build_context_from_files
from app.repo.repo_reader import RepoReaderError

DEFAULT_SAFETY_NOTES = [
    "This endpoint is read-only and does not apply the generated diff.",
    "Review the generated diff before making any manual changes.",
    "The planner is limited to the selected context files and may be incomplete if important files were omitted.",
]


def _extract_section(content: str, header: str, next_headers: list[str]) -> str:
    if next_headers:
        boundary = rf"(?=\n(?:{'|'.join(next_headers)}):|\Z)"
    else:
        boundary = r"(?=\Z)"
    pattern = rf"{header}:\s*(.*?){boundary}"
    match = re.search(pattern, content, flags=re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def _extract_code(content: str) -> str:
    match = re.search(r"CODE:\s*```text\s*(.*?)```", content, flags=re.DOTALL)
    if match:
        return match.group(1).rstrip()

    code_section = _extract_section(content, "CODE", [])
    return code_section.rstrip()


def _parse_plan_response(content: str) -> dict:
    explanation = _extract_section(content, "EXPLANATION", ["TARGET_FILE", "OPERATION", "ANCHOR", "CODE"])
    target_file = _extract_section(content, "TARGET_FILE", ["OPERATION", "ANCHOR", "CODE"]) or None
    operation = _extract_section(content, "OPERATION", ["ANCHOR", "CODE"])
    anchor = _extract_section(content, "ANCHOR", ["CODE"]) or None
    code = _extract_code(content)

    return {
        "explanation": explanation or "No explanation provided by the model.",
        "target_file": target_file,
        "operation": operation or "",
        "anchor": anchor,
        "code": code,
    }


def _read_project_file(project_path: str, relative_path: str) -> str:
    project_root = Path(project_path).resolve()
    target_path = (project_root / relative_path).resolve()
    if project_root not in {target_path, *target_path.parents}:
        raise RepoReaderError("Target file resolves outside the project root.")
    if not target_path.is_file():
        raise RepoReaderError(f"Target file does not exist: {relative_path}")
    return target_path.read_text(encoding="utf-8")


def _normalize_anchor(anchor: str) -> str:
    stripped = anchor.strip()
    fenced_match = re.fullmatch(r"```(?:text)?\s*(.*?)```", stripped, flags=re.DOTALL)
    if fenced_match:
        stripped = fenced_match.group(1).strip()
    return stripped


def _normalize_insert_block(code: str) -> str:
    stripped = code.strip()
    if not stripped:
        return ""
    return stripped


def _count_trailing_newlines(text: str) -> int:
    return len(text) - len(text.rstrip("\n"))


def _count_leading_newlines(text: str) -> int:
    return len(text) - len(text.lstrip("\n"))


def _format_inserted_block(original: str, insert_at: int, code: str) -> str:
    inserted = _normalize_insert_block(code)
    if not inserted:
        return original

    before = original[:insert_at]
    after = original[insert_at:]
    needed_before = max(0, 2 - _count_trailing_newlines(before))
    needed_after = max(0, 1 - _count_leading_newlines(after))
    before_padding = "\n" * needed_before
    after_padding = "\n" * needed_after
    return before + before_padding + inserted + after_padding + after


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


def _apply_insert_after_anchor(original: str, anchor: str, code: str) -> tuple[str | None, str | None]:
    if not anchor or not code.strip():
        return None, "Planner output is missing an anchor or insertable code."

    lines = original.splitlines(keepends=True)
    inserted_block = _normalize_insert_block(code)
    if not inserted_block:
        return None, "Planner output does not include any code to insert."

    anchor_name = _normalize_anchor(anchor)
    if not anchor_name:
        return None, "Planner output anchor is empty after normalization."

    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", anchor_name):
        function_patterns = (
            f"async def {anchor_name}(",
            f"def {anchor_name}(",
        )
        for index, line in enumerate(lines):
            if any(pattern in line for pattern in function_patterns):
                insert_at = _find_function_end(lines, index)
                char_offset = sum(len(current_line) for current_line in lines[:insert_at])
                return _format_inserted_block(original, char_offset, inserted_block), None

    if "\n" in anchor_name:
        anchor_index = original.find(anchor_name)
        if anchor_index != -1:
            insert_at = anchor_index + len(anchor_name)
            if insert_at < len(original) and original[insert_at] != "\n":
                next_newline = original.find("\n", insert_at)
                insert_at = len(original) if next_newline == -1 else next_newline + 1
            elif insert_at < len(original):
                insert_at += 1
            return _format_inserted_block(original, insert_at, inserted_block), None

    for index, line in enumerate(lines):
        if anchor_name in line:
            insert_at = index + 1
            char_offset = sum(len(current_line) for current_line in lines[:insert_at])
            return _format_inserted_block(original, char_offset, inserted_block), None

    return None, f"Anchor not found in target file: {anchor_name}"


def _generate_unified_diff(original: str, updated: str, relative_path: str) -> str:
    diff_lines = difflib.unified_diff(
        original.splitlines(),
        updated.splitlines(),
        fromfile=f"a/{relative_path}",
        tofile=f"b/{relative_path}",
        lineterm="",
    )
    return "\n".join(diff_lines)


def _validate_plan(
    target_file: str | None,
    operation: str,
    anchor: str | None,
    code: str,
    context_files: list[str],
) -> list[str]:
    warnings: list[str] = []
    if target_file and target_file not in context_files:
        warnings.append("Planner selected a target file that is not included in the provided context.")
    if operation and operation != "insert_after_anchor":
        warnings.append("Planner returned an unsupported operation.")
    if target_file and not anchor:
        warnings.append("Planner selected a target file but did not provide an anchor.")
    if target_file and not code.strip():
        warnings.append("Planner selected a target file but did not provide code to insert.")
    return warnings


async def plan_change(project_path: str, task: str, files: list[str]) -> dict:
    context_files = list(dict.fromkeys(files))
    context = build_context_from_files(project_path=project_path, relative_paths=context_files)

    prompt = (
        "You are a read-only coding assistant. "
        "You must not claim that you edited files. "
        "Follow the user's task exactly. "
        "Explicit 'do not ...' instructions in the task are mandatory. "
        "Return a structured change plan, not a unified diff. "
        "Return insertion code only for files from the provided context. "
        "If the context is insufficient, return no updated file, no code, and explain exactly which files are needed. "
        "Use only this exact format:\n\n"
        "EXPLANATION:\n"
        "<brief explanation>\n\n"
        "TARGET_FILE:\n"
        "<relative target file from context or empty>\n\n"
        "OPERATION:\n"
        "insert_after_anchor\n\n"
        "ANCHOR:\n"
        "<exact anchor text or function name>\n\n"
        "CODE:\n"
        "```text\n"
        "<full code block to insert>\n"
        "```\n\n"
        f"Task:\n{task}\n\n"
        f"{context}"
    )
    raw_response = await ask_ollama(prompt)
    proposal = _parse_plan_response(raw_response)
    warnings = _validate_plan(
        target_file=proposal["target_file"],
        operation=proposal["operation"],
        anchor=proposal["anchor"],
        code=proposal["code"],
        context_files=context_files,
    )
    generated_diff = ""

    if proposal["target_file"] and proposal["operation"] == "insert_after_anchor" and proposal["anchor"] and proposal["code"].strip():
        original = _read_project_file(project_path, proposal["target_file"])
        updated, apply_warning = _apply_insert_after_anchor(original, proposal["anchor"], proposal["code"])
        if apply_warning:
            warnings.append(apply_warning)
        elif updated is not None:
            generated_diff = _generate_unified_diff(original, updated, proposal["target_file"])

    safety_notes = list(DEFAULT_SAFETY_NOTES)
    if warnings:
        safety_notes.append("This proposal has warnings and should not be applied until reviewed.")

    return {
        "explanation": proposal["explanation"],
        "target_file": proposal["target_file"],
        "operation": proposal["operation"],
        "anchor": proposal["anchor"],
        "code": proposal["code"],
        "generated_diff": generated_diff,
        "context_files": context_files,
        "warnings": warnings,
        "safety_notes": safety_notes,
    }
