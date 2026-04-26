from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", ".env"),
        extra="ignore",
    )

    app_name: str = "Recursive Paper Study Tool"
    database_url: str = Field(
        default="postgresql+psycopg://study_user:study_password@db:5432/study_assistant",
        alias="DATABASE_URL",
    )
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_chat_completions_path: str = Field(default="/chat/completions", alias="OPENAI_CHAT_COMPLETIONS_PATH")
    model_name: str = Field(default="gpt-4.1-mini", alias="MODEL_NAME")
    llm_timeout_seconds: float = Field(default=120.0, alias="LLM_TIMEOUT_SECONDS")
    llm_max_tokens: int = Field(default=24000, alias="LLM_MAX_TOKENS")
    llm_json_mode: bool = Field(default=True, alias="LLM_JSON_MODE")
    allow_llm_fallback: bool = Field(default=False, alias="ALLOW_LLM_FALLBACK")
    enable_research_search: bool = Field(default=False, alias="ENABLE_RESEARCH_SEARCH")
    cors_origins_raw: str = Field(default="http://localhost:3000", alias="BACKEND_CORS_ORIGINS")
    storage_dir: str = "storage/uploads"
    assets_dir: str = "storage/assets"
    max_expand_depth: int = Field(default=10, alias="MAX_EXPAND_DEPTH")
    max_prerequisites_per_concept: int = Field(default=5, alias="MAX_PREREQUISITES_PER_CONCEPT")
    max_annotation_entities: int = Field(default=30, alias="MAX_ANNOTATION_ENTITIES")
    semantic_scholar_api_key: str | None = Field(default=None, alias="SEMANTIC_SCHOLAR_API_KEY")

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins_raw.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
