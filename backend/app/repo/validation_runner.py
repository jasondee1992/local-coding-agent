from __future__ import annotations

from typing import Any

import httpx


def _build_check_specs(
    include_version: bool,
    include_settings: bool,
    include_models: bool,
) -> list[tuple[str, str]]:
    checks: list[tuple[str, str]] = [("health", "/health")]
    if include_version:
        checks.append(("version", "/version"))
    if include_settings:
        checks.append(("settings", "/settings"))
    if include_models:
        checks.append(("models", "/models"))
    return checks


async def run_basic_validation(
    base_url: str = "http://localhost:8000",
    include_version: bool = True,
    include_settings: bool = True,
    include_models: bool = False,
) -> dict[str, Any]:
    normalized_base = base_url.rstrip("/")
    timeout = httpx.Timeout(10.0)
    checks: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=timeout) as client:
        for name, path in _build_check_specs(
            include_version=include_version,
            include_settings=include_settings,
            include_models=include_models,
        ):
            url = f"{normalized_base}{path}"
            try:
                response = await client.get(url)
                preview = response.text[:500]
                checks.append(
                    {
                        "name": name,
                        "url": url,
                        "ok": 200 <= response.status_code < 300,
                        "status_code": response.status_code,
                        "response_preview": preview,
                        "error": None,
                    }
                )
            except httpx.HTTPError as exc:
                checks.append(
                    {
                        "name": name,
                        "url": url,
                        "ok": False,
                        "status_code": None,
                        "response_preview": None,
                        "error": str(exc),
                    }
                )

    return {
        "ok": all(check["ok"] for check in checks),
        "checks": checks,
    }
