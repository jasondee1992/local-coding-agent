from fastapi import FastAPI

from app.config import get_settings
from app.llm.ollama_client import OllamaClient
from app.schemas.chat import ChatRequest, ChatResponse

settings = get_settings()
app = FastAPI(title=settings.app_name)


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
