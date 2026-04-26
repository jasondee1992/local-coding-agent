from __future__ import annotations

import httpx

from app.config import get_settings


def _base_url() -> str:
    return get_settings().ai_server_base_url.rstrip("/")


async def request_plan_from_context(task: str, context_files: list[dict]) -> dict:
    url = f"{_base_url()}/ai/plan-from-context"
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                url,
                json={
                    "task": task,
                    "files": context_files,
                },
            )
    except httpx.RequestError as exc:
        raise RuntimeError(f"AI server unreachable at {url}: {exc}") from exc

    if response.status_code != 200:
        detail = response.text.strip() or response.reason_phrase
        raise RuntimeError(f"AI server returned {response.status_code} for /ai/plan-from-context: {detail}")
    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError("AI server returned invalid JSON for /ai/plan-from-context.") from exc


async def ping_ai_server() -> dict:
    url = f"{_base_url()}/health"
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.get(url)
    except httpx.RequestError as exc:
        raise RuntimeError(f"AI server unreachable at {url}: {exc}") from exc

    if response.status_code != 200:
        detail = response.text.strip() or response.reason_phrase
        raise RuntimeError(f"AI server returned {response.status_code} for /health: {detail}")
    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError("AI server returned invalid JSON for /health.") from exc
