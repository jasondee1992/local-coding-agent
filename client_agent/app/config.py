from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    client_agent_name: str = "Local Workspace Agent"
    client_agent_env: str = "development"
    ai_server_base_url: str = "http://localhost:8000"
    client_max_file_size_kb: int = 300
    client_proposals_dir: str = "proposals"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
