import re

from app.llm.ollama_client import ask_ollama
from app.repo.context_builder import build_context_from_files

DEFAULT_SAFETY_NOTES = [
    "This endpoint is read-only and does not apply the proposed diff.",
    "Review the diff before making any manual changes.",
    "The proposal is limited to the selected context files and may be incomplete if important files were omitted.",
]


def _extract_section(content: str, header: str, next_headers: list[str]) -> str:
    pattern = rf"{header}:\s*(.*?)(?=\n(?:{'|'.join(next_headers)}):|\Z)"
    match = re.search(pattern, content, flags=re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def _extract_diff(content: str) -> str:
    match = re.search(r"DIFF:\s*```diff\s*(.*?)```", content, flags=re.DOTALL)
    if match:
        return match.group(1).strip()

    diff_section = _extract_section(content, "DIFF", ["SAFETY_NOTES", "EXPLANATION"])
    return diff_section.strip()


def _extract_safety_notes(content: str) -> list[str]:
    notes_section = _extract_section(content, "SAFETY_NOTES", ["EXPLANATION", "DIFF"])
    if not notes_section:
        return DEFAULT_SAFETY_NOTES

    notes: list[str] = []
    for line in notes_section.splitlines():
        cleaned = line.strip().lstrip("-").strip()
        if cleaned:
            notes.append(cleaned)

    return notes or DEFAULT_SAFETY_NOTES


def _parse_proposal_response(content: str) -> dict:
    explanation = _extract_section(content, "EXPLANATION", ["DIFF", "SAFETY_NOTES"])
    diff = _extract_diff(content)
    safety_notes = _extract_safety_notes(content)

    return {
        "explanation": explanation or "No explanation provided by the model.",
        "diff": diff,
        "safety_notes": safety_notes,
    }


def _extract_added_lines(diff: str) -> list[str]:
    added_lines: list[str] = []
    for line in diff.splitlines():
        if line.startswith("+++") or not line.startswith("+"):
            continue
        added_lines.append(line[1:])
    return added_lines


def _extract_non_removed_code_lines(diff: str) -> list[str]:
    lines: list[str] = []
    for line in diff.splitlines():
        if (
            line.startswith("diff --git")
            or line.startswith("index ")
            or line.startswith("--- ")
            or line.startswith("+++ ")
            or line.startswith("@@")
            or line.startswith("-")
        ):
            continue
        if line.startswith("+") or line.startswith(" "):
            lines.append(line[1:])
    return lines


def _extract_task_paths(task: str) -> list[str]:
    return sorted(set(re.findall(r"(?<!\w)(/[A-Za-z0-9._\-/]+)", task)))


def _task_mentions_endpoint_route(task: str) -> bool:
    lowered = task.lower()
    return "endpoint" in lowered or "route" in lowered


def _context_includes_fastapi_python_file(context_files: set[str]) -> bool:
    return any(
        (
            path.startswith("backend/app/")
            or path.startswith("app/")
        )
        and path.endswith(".py")
        for path in context_files
    )


def _task_mentions(task: str, *phrases: str) -> bool:
    lowered = task.lower()
    return any(phrase in lowered for phrase in phrases)


def _extract_import_modules(lines: list[str]) -> list[str]:
    modules: list[str] = []
    for line in lines:
        stripped = line.strip()
        match = re.match(r"from\s+([a-zA-Z_][\w.]*)\s+import\b", stripped)
        if match:
            modules.append(match.group(1))
            continue
        match = re.match(r"import\s+([a-zA-Z_][\w.]*)\b", stripped)
        if match:
            modules.append(match.group(1))
    return modules


def validate_proposed_diff(
    diff: str,
    task: str = "",
    context_files: list[str] | None = None,
) -> list[str]:
    """Return non-blocking warnings for incomplete or suspicious proposed diffs.

    Example:
        A task like "add endpoint /version" should warn if the diff adds code
        but does not introduce an added route line for "/version".
    """
    warnings: list[str] = []
    stripped_diff = diff.strip()
    context_file_set = set(context_files or [])

    if not stripped_diff:
        return ["Proposed diff is empty."]

    if "--- " not in diff or "+++ " not in diff:
        warnings.append("Proposed diff is non-empty but is missing unified diff file headers ('--- ' and '+++ ').")

    added_files = set(re.findall(r"^\+\+\+\s+(?:b/)?([^\s]+)", diff, flags=re.MULTILINE))
    added_lines = _extract_added_lines(diff)
    non_removed_lines = _extract_non_removed_code_lines(diff)
    added_text = "\n".join(added_lines)
    schema_imports = set(
        re.findall(
            r"(?:from\s+app\.schemas\.([a-zA-Z_][a-zA-Z0-9_]*)\s+import|import\s+app\.schemas\.([a-zA-Z_][a-zA-Z0-9_]*))",
            added_text,
        )
    )

    for schema_from, schema_import in sorted(schema_imports):
        schema_name = schema_from or schema_import
        expected_path = f"backend/app/schemas/{schema_name}.py"
        if expected_path not in added_files:
            warnings.append(
                f"Diff imports app.schemas.{schema_name} but does not include {expected_path}."
            )

    if (
        "from app.schemas.version import VersionResponse" in added_text
        and "backend/app/schemas/version.py" not in added_files
    ):
        warnings.append(
            "Diff references 'from app.schemas.version import VersionResponse' without adding backend/app/schemas/version.py."
        )

    if _task_mentions(task, "do not use response_model") and "response_model=" in added_text:
        warnings.append("Task says not to use response_model, but the diff adds response_model usage.")

    if _task_mentions(task, "plain dictionary", "plain dict"):
        if re.search(r"return\s+[A-Z][A-Za-z0-9_]*(?:Request|Response)\s*\(", added_text):
            warnings.append(
                "Task asks for a plain dictionary response, but the diff appears to return a response schema object."
            )

    if _task_mentions(task, "do not create a schema file", "do not create schema"):
        if "app.schemas." in added_text:
            warnings.append("Task says not to create/use a schema file, but the diff imports from app.schemas.")
        if any(path.startswith("backend/app/schemas/") for path in added_files):
            warnings.append("Task says not to create/use a schema file, but the diff creates a schema file.")
        schema_context_present = any(path.startswith("backend/app/schemas/") for path in context_file_set) or any(
            path.startswith("app/schemas/") for path in context_file_set
        )
        if not schema_context_present and re.search(r"\b[A-Z][A-Za-z0-9_]*(?:Request|Response)\b", added_text):
            warnings.append(
                "Task says not to create/use a schema file, but the diff references request/response schema classes."
            )

    module_imports = set(
        re.findall(
            r"from\s+app\.([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\s+import",
            added_text,
        )
    )
    module_imports.update(
        re.findall(
            r"import\s+app\.([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)",
            added_text,
        )
    )

    for package_name, module_name in sorted(module_imports):
        expected_path = f"backend/app/{package_name}/{module_name}.py"
        if expected_path not in added_files and expected_path not in context_file_set:
            warnings.append("Diff may reference a module that is not included in the patch.")
            break

    added_import_modules = _extract_import_modules(added_lines)
    visible_import_modules = _extract_import_modules(non_removed_lines)
    for module_name in sorted(set(added_import_modules)):
        if visible_import_modules.count(module_name) > 1:
            warnings.append(
                f"Diff appears to add a duplicate import from {module_name}; reuse the existing import if possible."
            )
            break

    suspicious_commands = ("sudo ", "rm -rf", "git ", "curl ", "wget ", "chmod ", "chown ")
    for stripped_line in added_lines:
        stripped_line = stripped_line.lstrip()
        if not stripped_line:
            continue
        if stripped_line.startswith(suspicious_commands):
            warnings.append(f"Diff contains suspicious command-like content: {stripped_line}")
            break

    task_paths = _extract_task_paths(task)
    if task_paths and _task_mentions_endpoint_route(task) and _context_includes_fastapi_python_file(context_file_set):
        for task_path in task_paths:
            route_patterns = (
                f'@app.get("{task_path}")',
                f'@app.post("{task_path}")',
                f'@router.get("{task_path}")',
                f'@router.post("{task_path}")',
            )
            if not any(pattern in line for pattern in route_patterns for line in added_lines) and not any(
                task_path in line for line in added_lines
            ):
                warnings.append(
                    f"Task mentions endpoint {task_path}, but the diff does not appear to add or modify a route for it."
                )

    if _task_mentions(task, "simple /version endpoint"):
        post_patterns = (
            '@app.post("/version")',
            '@router.post("/version")',
        )
        if any(pattern in line for pattern in post_patterns for line in added_lines):
            warnings.append(
                "Task asks for a simple /version endpoint; consider GET instead of POST unless the task asks for POST."
            )

    if _task_mentions(task, "ollama model", "configured ollama model") and "OllamaClient(" in added_text:
        warnings.append(
            "Diff appears to instantiate OllamaClient unnecessarily; settings.ollama_model is sufficient for this task."
        )

    return warnings


async def propose_patch(project_path: str, task: str, files: list[str]) -> dict:
    context = build_context_from_files(project_path=project_path, relative_paths=files)

    prompt = (
        "You are a read-only coding assistant. "
        "You must not claim that you edited files. "
        "Follow the user's task exactly. "
        "Hard user constraints: explicit 'do not ...' instructions in the task are mandatory. "
        "If you cannot satisfy all hard constraints, return an empty diff and explain what context is missing. "
        "Never contradict hard constraints in safety notes. "
        "Safety notes must accurately describe the actual diff. "
        "Return a complete unified diff that applies cleanly from the repository root, based only on the provided file context. "
        "The diff must be self-contained. "
        "The diff must compile conceptually after applying. "
        "The diff must not reference missing modules. "
        "Prefer using existing variables already present in the selected file. "
        "Include every new file required by the change. "
        "Do not invent imports. "
        "Do not add imports unless required. "
        "If you introduce an import from a new module, you must include that new module file in the diff. "
        "If an import already exists through a grouped import, do not add a duplicate import for the same module. "
        "Do not add imports for files that are not included in the provided context unless the diff also creates those files. "
        "Do not add a new import only to read a value already available from settings. "
        "Do not instantiate clients or services unless required. "
        "For simple endpoints that return config values, use the existing settings object directly. "
        "If the user says not to create a new schema file, then do not import or reference any new schema. "
        "For simple FastAPI utility endpoints, prefer returning a plain dict and do not use response_model unless the requested file context already contains a suitable existing schema. "
        "If the task asks to add an endpoint, the diff must include the corresponding route decorator or router registration. "
        "Do not satisfy an endpoint-addition task by modifying a different endpoint. "
        "If you are unsure where to add the endpoint, return an empty diff and ask for the relevant routing file. "
        "Prefer minimal changes within the provided files. "
        "Do not invent new files unless they are required to make the patch complete. "
        "If a complete patch cannot be made using the selected files, return an empty diff and clearly list the additional files needed. "
        "Do not reference files in the explanation or safety notes unless they are included in the provided context, included in the diff, or explicitly listed as needed files. "
        "Avoid adding new Pydantic schemas for simple endpoints unless explicitly requested; simple dict responses are acceptable for small utility endpoints. "
        "Do not include unrelated files. "
        "Do not include commands to run. "
        "Do not include secrets. "
        "Keep the patch minimal.\n\n"
        "Return output in this exact format:\n"
        "EXPLANATION:\n"
        "<brief explanation>\n\n"
        "DIFF:\n"
        "```diff\n"
        "<unified diff here>\n"
        "```\n\n"
        "SAFETY_NOTES:\n"
        "- <note 1>\n"
        "- <note 2>\n\n"
        f"Task:\n{task}\n\n"
        f"{context}"
    )
    raw_response = await ask_ollama(prompt)
    proposal = _parse_proposal_response(raw_response)
    proposal["context_files"] = list(dict.fromkeys(files))
    proposal["warnings"] = validate_proposed_diff(
        proposal["diff"],
        task=task,
        context_files=proposal["context_files"],
    )
    if proposal["warnings"]:
        warning_note = "This proposal has warnings and should not be applied until reviewed."
        constraint_note = (
            "This proposal violates or may violate explicit task constraints and should not be applied until fixed."
        )
        if warning_note not in proposal["safety_notes"]:
            proposal["safety_notes"].append(warning_note)
        if constraint_note not in proposal["safety_notes"]:
            proposal["safety_notes"].append(constraint_note)
    return proposal
