from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


def _backend_relative(path: str) -> Path:
    return (BACKEND_DIR / path).resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://worldfork:worldfork@localhost:5432/worldfork"
    artifact_root: Path = _backend_relative("../artifacts")
    source_of_truth_dir: Path = _backend_relative("../source_of_truth")
    auto_create_tables: bool = False
    default_llm_provider: str = "openrouter"
    fallback_model: str = "openai/gpt-4o-mini"
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_chat_completions_url: str = "https://openrouter.ai/api/v1/chat/completions"
    openrouter_http_referer: str = "http://localhost:8003"
    openrouter_title: str = "WorldFork"
    redis_url: str = "redis://localhost:6379/0"
    default_model: str = "openai/gpt-5.4"
    initializer_agent_model: str = "openai/gpt-5.4"
    god_agent_model: str = "openai/gpt-5.4"
    cohort_agent_model: str = "openai/gpt-5.4"
    hero_agent_model: str = "openai/gpt-5.4"
    event_summary_model: str = "openai/gpt-5.4"
    report_agent_model: str = "openai/gpt-5.4"
    app_name: str = "WorldFork Backend"
    api_prefix: str = "/api"
    default_tick_duration: str = "1 day"
    default_max_ticks: int = 12
    default_max_branch_depth: int = 3
    default_max_active_multiverses: int = 12
    default_max_branches_per_tick: int = 2
    branch_score_threshold: float = 0.7
    initializer_direct_context_char_budget: int = 18000
    initializer_chunk_chars: int = 12000
    initializer_chunk_overlap_chars: int = 800
    llm_max_retries: int = 3
    llm_retry_backoff_seconds: float = 1.5
    cors_origins: list[str] = Field(default_factory=list)

    @field_validator("artifact_root", "source_of_truth_dir", mode="after")
    @classmethod
    def resolve_backend_relative_path(cls, value: Path) -> Path:
        if value.is_absolute():
            return value.resolve()
        return (BACKEND_DIR / value).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
