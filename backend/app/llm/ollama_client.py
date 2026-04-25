import httpx
from fastapi import HTTPException, status

from app.config import Settings, get_settings


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self._timeout = httpx.Timeout(float(settings.ollama_timeout_seconds), connect=5.0)

    def _build_generate_payload(
        self,
        prompt: str,
        *,
        num_predict: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> dict:
        return {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self._settings.ollama_keep_alive,
            "options": {
                "num_predict": (
                    self._settings.ollama_num_predict if num_predict is None else num_predict
                ),
                "temperature": (
                    self._settings.ollama_temperature
                    if temperature is None
                    else temperature
                ),
                "top_p": self._settings.ollama_top_p if top_p is None else top_p,
            },
        }

    async def _request(self, method: str, path: str, *, json: dict | None = None) -> httpx.Response:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(method, f"{self._base_url}{path}", json=json)
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

        if response.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Ollama returned an error: {response.status_code}",
            )

        return response

    async def generate(
        self,
        message: str,
        *,
        num_predict: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> str:
        payload = self._build_generate_payload(
            message,
            num_predict=num_predict,
            temperature=temperature,
            top_p=top_p,
        )
        response = await self._request("POST", "/api/generate", json=payload)

        try:
            data = response.json()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Ollama returned an invalid response payload.",
            ) from exc

        model_response = data.get("response")
        if not isinstance(model_response, str):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Ollama returned an invalid response payload.",
            )

        return model_response


async def ask_ollama(message: str) -> str:
    client = OllamaClient(get_settings())
    return await client.generate(message)


async def list_ollama_models() -> list[dict]:
    client = OllamaClient(get_settings())
    response = await client._request("GET", "/api/tags")

    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ollama returned an invalid response payload.",
        ) from exc

    models = data.get("models")
    if not isinstance(models, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ollama returned an invalid models payload.",
        )

    return [model for model in models if isinstance(model, dict)]


async def warm_up_ollama() -> str:
    client = OllamaClient(get_settings())
    return await client.generate(
        "Reply with OK only.",
        num_predict=8,
        temperature=0.0,
        top_p=0.1,
    )
