from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from app.config import get_settings
from app.proposal_store import load_client_proposal


@dataclass(frozen=True)
class ParsedHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    before_context: list[str]
    added_lines: list[str]
    after_context: list[str]


def _client_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _proposals_dir() -> Path:
    return _client_root() / get_settings().client_proposals_dir


def _build_response(
    proposal_id: str,
    *,
    applied: bool,
    target_file: str | None,
    backup_path: str | None,
    message: str,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "proposal_id": proposal_id,
        "applied": applied,
        "target_file": target_file,
        "backup_path": backup_path,
        "message": message,
        "warnings": list(warnings or []),
    }


def _validate_target_file(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Proposal target_file is missing.")
    if cleaned.startswith(("/", "\\")) or "\\" in cleaned:
        raise ValueError("Proposal target_file must be relative to project_path.")
    normalized = PurePosixPath(cleaned)
    if any(part in {"", ".", ".."} for part in normalized.parts):
        raise ValueError("Proposal target_file contains unsafe path segments.")
    return normalized.as_posix()


def _resolve_target_path(project_path: str, target_file: str) -> Path:
    project_root = Path(project_path.strip()).resolve()
    if not project_root.is_dir():
        raise ValueError("Proposal project_path does not exist.")
    safe_target = _validate_target_file(target_file)
    target_path = (project_root / safe_target).resolve()
    if project_root not in {target_path, *target_path.parents}:
        raise ValueError("Target file resolves outside project_path.")
    if not target_path.is_file():
        raise ValueError("Target file does not exist.")
    return target_path


def _normalize_diff_path(raw_path: str) -> str:
    cleaned = raw_path.strip().split("\t", 1)[0]
    if cleaned == "/dev/null":
        raise ValueError("Creation or deletion patches are not supported.")
    if cleaned.startswith(("a/", "b/")):
        cleaned = cleaned[2:]
    return _validate_target_file(cleaned)


def _parse_hunk_header(line: str) -> tuple[int, int, int, int]:
    match = re.fullmatch(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
    if not match:
        raise ValueError("Diff contains an invalid hunk header.")
    return (
        int(match.group(1)),
        int(match.group(2) or "1"),
        int(match.group(3)),
        int(match.group(4) or "1"),
    )


def _parse_unified_diff(diff_text: str, expected_target: str) -> ParsedHunk:
    lines = diff_text.splitlines()
    header_indexes = [index for index, line in enumerate(lines) if line.startswith("--- ")]
    plus_indexes = [index for index, line in enumerate(lines) if line.startswith("+++ ")]
    if len(header_indexes) != 1 or len(plus_indexes) != 1:
        raise ValueError("Diff must contain exactly one file header.")
    header_index = header_indexes[0]
    plus_index = plus_indexes[0]
    if plus_index != header_index + 1:
        raise ValueError("Diff headers are malformed.")

    old_path = _normalize_diff_path(lines[header_index][4:])
    new_path = _normalize_diff_path(lines[plus_index][4:])
    if old_path != new_path or old_path != expected_target:
        raise ValueError("Diff target file does not match the saved proposal target_file.")

    hunk_indexes = [index for index, line in enumerate(lines) if line.startswith("@@ ")]
    if len(hunk_indexes) != 1:
        raise ValueError("Only single-hunk insertion diffs are supported.")

    hunk_index = hunk_indexes[0]
    old_start, old_count, new_start, new_count = _parse_hunk_header(lines[hunk_index])
    body_lines = lines[hunk_index + 1 :]
    if not body_lines:
        raise ValueError("Diff hunk is empty.")

    before_context: list[str] = []
    added_lines: list[str] = []
    after_context: list[str] = []
    seen_addition = False
    finished_addition = False

    for line in body_lines:
        if line.startswith("\\"):
            continue
        if not line:
            raise ValueError("Diff body contains an invalid empty line.")
        marker = line[0]
        content = line[1:]
        if marker == "-":
            raise ValueError("Removal patches are not supported.")
        if marker == "+":
            if finished_addition:
                raise ValueError("Diff contains multiple insertion blocks in one hunk.")
            seen_addition = True
            added_lines.append(content)
            continue
        if marker != " ":
            raise ValueError("Diff contains unsupported line markers.")
        if not seen_addition:
            before_context.append(content)
        else:
            finished_addition = True
            after_context.append(content)

    if not added_lines:
        raise ValueError("Diff does not contain any added lines.")

    expected_old_count = len(before_context) + len(after_context)
    expected_new_count = expected_old_count + len(added_lines)
    if old_count != expected_old_count or new_count != expected_new_count:
        raise ValueError("Diff hunk line counts do not match its contents.")

    return ParsedHunk(
        old_start=old_start,
        old_count=old_count,
        new_start=new_start,
        new_count=new_count,
        before_context=before_context,
        added_lines=added_lines,
        after_context=after_context,
    )


def _find_subsequence(lines: list[str], needle: list[str]) -> list[int]:
    if not needle:
        return []
    limit = len(lines) - len(needle) + 1
    if limit < 0:
        return []
    return [
        index for index in range(limit)
        if lines[index : index + len(needle)] == needle
    ]


def _matches_at(lines: list[str], start: int, needle: list[str]) -> bool:
    return start >= 0 and lines[start : start + len(needle)] == needle


def _locate_insertion_index(current_lines: list[str], hunk: ParsedHunk) -> tuple[int | None, str | None]:
    if _find_subsequence(current_lines, hunk.added_lines):
        return None, "Change already appears to exist."

    old_block = hunk.before_context + hunk.after_context
    if not old_block:
        return None, "Diff does not include enough context to apply safely."

    new_block = hunk.before_context + hunk.added_lines + hunk.after_context
    expected_start = hunk.old_start - 1
    if _matches_at(current_lines, expected_start, new_block):
        return None, "Change already appears to exist."
    if _matches_at(current_lines, expected_start, old_block):
        return expected_start + len(hunk.before_context), None

    exact_matches = _find_subsequence(current_lines, old_block)
    if len(exact_matches) == 1:
        return exact_matches[0] + len(hunk.before_context), None
    if _find_subsequence(current_lines, new_block):
        return None, "Change already appears to exist."
    if not exact_matches:
        return None, "Current file does not match the expected pre-apply context."
    return None, "Insertion point is ambiguous in the current file."


def _render_updated_text(original_text: str, current_lines: list[str], insertion_index: int, added_lines: list[str]) -> str:
    newline = "\r\n" if "\r\n" in original_text else "\n"
    updated_lines = current_lines[:insertion_index] + added_lines + current_lines[insertion_index:]
    rendered = newline.join(updated_lines)
    if original_text.endswith(("\n", "\r\n")):
        rendered += newline
    return rendered


def _backup_path(proposal_id: str, target_file: str) -> Path:
    safe_target_name = target_file.replace("/", "__")
    return _proposals_dir() / "backups" / proposal_id / f"{safe_target_name}.bak"


def apply_client_proposal(
    proposal_id: str,
    confirm_apply: bool,
    allow_warnings: bool = False,
    create_backup: bool = True,
) -> dict:
    try:
        proposal = load_client_proposal(proposal_id)
    except FileNotFoundError:
        return _build_response(
            proposal_id=proposal_id,
            applied=False,
            target_file=None,
            backup_path=None,
            message="Proposal not found.",
        )
    except ValueError as exc:
        return _build_response(
            proposal_id=proposal_id,
            applied=False,
            target_file=None,
            backup_path=None,
            message=str(exc),
        )

    target_file = proposal.get("target_file")
    warnings = list(proposal.get("warnings", []))
    if not confirm_apply:
        return _build_response(
            proposal_id=proposal_id,
            applied=False,
            target_file=target_file,
            backup_path=None,
            message="confirm_apply=true is required.",
            warnings=warnings,
        )
    if warnings and not allow_warnings:
        return _build_response(
            proposal_id=proposal_id,
            applied=False,
            target_file=target_file,
            backup_path=None,
            message="Proposal has warnings. Re-run with allow_warnings=true to apply anyway.",
            warnings=warnings,
        )

    generated_diff = str(proposal.get("generated_diff", "")).strip()
    if not generated_diff:
        return _build_response(
            proposal_id=proposal_id,
            applied=False,
            target_file=target_file,
            backup_path=None,
            message="Proposal generated_diff is empty.",
            warnings=warnings,
        )

    try:
        safe_target_file = _validate_target_file(str(target_file or ""))
        target_path = _resolve_target_path(str(proposal.get("project_path", "")), safe_target_file)
        parsed_hunk = _parse_unified_diff(generated_diff, safe_target_file)
    except ValueError as exc:
        return _build_response(
            proposal_id=proposal_id,
            applied=False,
            target_file=target_file,
            backup_path=None,
            message=str(exc),
            warnings=warnings,
        )

    original_text = target_path.read_text(encoding="utf-8")
    current_lines = original_text.splitlines()
    insertion_index, locate_message = _locate_insertion_index(current_lines, parsed_hunk)
    if insertion_index is None:
        return _build_response(
            proposal_id=proposal_id,
            applied=False,
            target_file=safe_target_file,
            backup_path=None,
            message=locate_message or "Unable to locate insertion point.",
            warnings=warnings,
        )

    backup_path: Path | None = None
    if create_backup:
        backup_path = _backup_path(proposal_id, safe_target_file)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target_path, backup_path)

    updated_text = _render_updated_text(original_text, current_lines, insertion_index, parsed_hunk.added_lines)
    target_path.write_text(updated_text, encoding="utf-8")
    return _build_response(
        proposal_id=proposal_id,
        applied=True,
        target_file=safe_target_file,
        backup_path=str(backup_path) if backup_path else None,
        message="Proposal applied successfully.",
        warnings=warnings,
    )
