from fastapi import FastAPI, HTTPException, status

from app.config import get_settings
from app.llm.ollama_client import (
    OllamaClient,
    ask_ollama,
    list_ollama_models,
    warm_up_ollama,
)
from app.repo.context_builder import build_context_from_files, build_repo_overview
from app.repo.repo_reader import RepoReaderError, scan_repo
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.models import ModelInfo, ModelsResponse, SettingsResponse, WarmupResponse
from app.schemas.repo import (
    RepoAskRequest,
    RepoAskResponse,
    RepoFile,
    RepoScanRequest,
    RepoScanResponse,
    RepoSummaryRequest,
    RepoSummaryResponse,
)

settings = get_settings()
app = FastAPI(title=settings.app_name)

DEFAULT_REPO_ASK_FILES = [
    "README.md",
    "backend/README.md",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "backend/requirements.txt",
    "backend/app/main.py",
    "backend/app/config.py",
    "backend/app/llm/ollama_client.py",
    "app/main.py",
    "src/app/page.tsx",
    "src/app/api/chat/route.ts",
]


def _repo_bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _select_context_files(request: RepoAskRequest) -> list[str]:
    if request.files:
        selected_files = list(dict.fromkeys(path.strip() for path in request.files if path.strip()))
        if not selected_files:
            raise _repo_bad_request("No valid file paths were provided.")
        if len(selected_files) > request.max_files:
            return selected_files[: request.max_files]
        return selected_files

    scanned_files = scan_repo(project_path=request.project_path, max_files=1000)
    available_paths = [file_info.relative_path for file_info in scanned_files]
    available_set = set(available_paths)

    selected_files: list[str] = []
    for path in DEFAULT_REPO_ASK_FILES:
        if path in available_set and path not in selected_files:
            selected_files.append(path)
        if len(selected_files) >= request.max_files:
            return selected_files

    for path in available_paths:
        if path not in selected_files:
            selected_files.append(path)
        if len(selected_files) >= request.max_files:
            break

    return selected_files


@app.get("/settings", response_model=SettingsResponse)
async def app_settings() -> SettingsResponse:
    return SettingsResponse(
        app_name=settings.app_name,
        app_env=settings.app_env,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
        ollama_timeout_seconds=settings.ollama_timeout_seconds,
        ollama_keep_alive=settings.ollama_keep_alive,
        ollama_num_predict=settings.ollama_num_predict,
        ollama_temperature=settings.ollama_temperature,
        ollama_top_p=settings.ollama_top_p,
        max_file_size_kb=settings.max_file_size_kb,
    )


@app.get("/models", response_model=ModelsResponse)
async def models() -> ModelsResponse:
    raw_models = await list_ollama_models()
    return ModelsResponse(
        models=[
            ModelInfo(
                name=str(model.get("name", "")),
                modified_at=(
                    str(model.get("modified_at"))
                    if model.get("modified_at") is not None
                    else None
                ),
                size=model.get("size") if isinstance(model.get("size"), int) else None,
            )
            for model in raw_models
            if model.get("name")
        ]
    )


@app.post("/warmup", response_model=WarmupResponse)
async def warmup() -> WarmupResponse:
    response = await warm_up_ollama()
    return WarmupResponse(response=response)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "model": settings.ollama_model,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    client = OllamaClient(settings)
    response = await client.generate(payload.message)
    return ChatResponse(response=response)


@app.post("/repo/scan", response_model=RepoScanResponse)
async def repo_scan(payload: RepoScanRequest) -> RepoScanResponse:
    try:
        files = scan_repo(project_path=payload.project_path, max_files=payload.max_files)
    except RepoReaderError as exc:
        raise _repo_bad_request(str(exc)) from exc

    return RepoScanResponse(
        project_path=payload.project_path,
        files=[
            RepoFile(
                path=file_info.relative_path,
                size_bytes=file_info.size,
                extension=file_info.extension,
            )
            for file_info in files
        ],
    )


@app.post("/repo/summary", response_model=RepoSummaryResponse)
async def repo_summary(payload: RepoSummaryRequest) -> RepoSummaryResponse:
    try:
        summary = build_repo_overview(project_path=payload.project_path, max_files=payload.max_files)
    except RepoReaderError as exc:
        raise _repo_bad_request(str(exc)) from exc

    return RepoSummaryResponse(summary=summary)


@app.post("/repo/ask", response_model=RepoAskResponse)
async def repo_ask(payload: RepoAskRequest) -> RepoAskResponse:
    try:
        context_files = _select_context_files(payload)
        context = build_context_from_files(
            project_path=payload.project_path,
            relative_paths=context_files,
        )
    except RepoReaderError as exc:
        raise _repo_bad_request(str(exc)) from exc

    prompt = (
        "You are a read-only coding assistant. "
        "Be concise by default. "
        "Use bullets only when useful. "
        "Do not repeat the whole file content. "
        "Answer based only on the provided repository context. "
        "Do not claim that you edited files. "
        "If context is insufficient, say exactly which files are needed.\n\n"
        f"Question:\n{payload.question}\n\n"
        f"{context}"
    )
    response = await ask_ollama(prompt)
    return RepoAskResponse(response=response, context_files=context_files)
