"""Settings from environment / .env (never committed)."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    data_dir: Path = PROJECT_ROOT / "data" / "raw"
    model_dir: Path = PROJECT_ROOT / "models"
    random_state: int = 42
    test_size: float = 0.2
    cv_folds: int = 5
    interpretability_tolerance: float = 0.02   # choose LogisticRegression if its CV AUC is within this of the best
    decision_threshold: float = 0.5

    # LLM advisor (optional narrative on top of the model)
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2"
    ollama_num_thread: int | None = None
    ollama_keep_alive: int = 60
    roles_file: Path = PROJECT_ROOT / "feasibility" / "roles.yaml"
    audit_log_path: Path | None = PROJECT_ROOT / "logs" / "audit.jsonl"

    @field_validator("audit_log_path", "ollama_num_thread", mode="before")
    @classmethod
    def _empty_is_none(cls, v):
        return None if v == "" else v


@lru_cache
def get_settings() -> Settings:
    return Settings()
