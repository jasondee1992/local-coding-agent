from pydantic import BaseModel


class ModelInfo(BaseModel):
    name: str
    modified_at: str | None = None
    size: int | None = None


class ModelsResponse(BaseModel):
    models: list[ModelInfo]


class SettingsResponse(BaseModel):
    app_name: str
    app_env: str
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_seconds: int
    ollama_keep_alive: str
    ollama_num_predict: int
    ollama_temperature: float
    ollama_top_p: float
    max_file_size_kb: int


class WarmupResponse(BaseModel):
    response: str
