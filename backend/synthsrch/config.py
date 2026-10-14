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

    nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nim_api_key: str = ""
    nim_model: str = "nvidia/nemotron-3.5-lightning-30b-a3b"

    tavily_api_key: str = ""
    exa_api_key: str = ""
    serper_api_key: str = ""
    linkup_api_key: str = ""
    firecrawl_api_key: str = ""

    extract_max_chars: int = 6000
    search_timeout_s: float = 15.0
    extract_timeout_s: float = 15.0

    # IDs verified against the live NIM catalog (Oct 2026). Custom IDs still allowed.
    NIM_MODELS: list[str] = [
        "nvidia/nemotron-3.5-lightning-30b-a3b",
        "openai/gpt-oss-20b",
        "mistralai/mistral-large-2-instruct",
        "mistralai/mixtral-8x22b-v0.1",
        "nvidia/llama-3.1-nemotron-70b-instruct",
        "mistralai/mistral-7b-instruct-v0.3",
    ]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    s.db_path.parent.mkdir(parents=True, exist_ok=True)
    return s
