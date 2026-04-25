import httpx
from fastapi import HTTPException, status

from app.config import Settings


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self._timeout = httpx.Timeout(30.0, connect=5.0)

    async def generate(self, message: str) -> str:
        payload = {
            "model": self._model,
            "prompt": message,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(f"{self._base_url}/api/generate", json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Ollama request timed out.",
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Ollama is not reachable. Confirm it is running locally.",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Ollama returned an error: {exc.response.status_code}",
            ) from exc

        data = response.json()
        model_response = data.get("response")
        if not isinstance(model_response, str):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Ollama returned an invalid response payload.",
            )

        return model_response
