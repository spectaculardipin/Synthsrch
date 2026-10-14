"""App configuration — pydantic-settings, local-first defaults."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_db_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "synthsrch" / "synthsrch.db"
    return Path.home() / ".synthsrch" / "synthsrch.db"


def default_data_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "synthsrch"
    return Path.home() / ".synthsrch"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SYNTHSRCH_", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8765
    # Factories (not import-time defaults) so tests can isolate by overriding
    # the cached instance's paths, and late env changes are respected.
    data_dir: Path = Field(default_factory=default_data_dir)
    db_path: Path = Field(default_factory=default_db_path)

    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    tavily_api_key: str = ""
    exa_api_key: str = ""
    serper_api_key: str = ""
    linkup_api_key: str = ""
    firecrawl_api_key: str = ""

    extract_max_chars: int = 6000
    search_timeout_s: float = 15.0
    extract_timeout_s: float = 15.0

    GROQ_MODELS: list[str] = [
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "qwen/qwen3.8-27b",
    ]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    s.db_path.parent.mkdir(parents=True, exist_ok=True)
    return s
