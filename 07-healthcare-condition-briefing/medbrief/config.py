"""Settings from environment / .env (never committed - see .env.example)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: Literal["ollama", "bedrock"] = "ollama"
    embedding_provider: Literal["ollama", "bedrock"] = "ollama"
    temperature: float = 0.0
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_vision_model: str = "gemma3:4b"       # figure captioning (any Ollama vision model)
    ollama_num_ctx: int = 6144                   # a briefing prompt carries evidence for every section
    ollama_num_thread: int | None = None
    ollama_keep_alive: int = 60
    ollama_num_predict: int = 650
    aws_region: str = "us-east-1"
    bedrock_model_id: str | None = None
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"

    data_dir: Path = PROJECT_ROOT / "data" / "raw"
    extracted_dir: Path = PROJECT_ROOT / "data" / "extracted"
    chroma_dir: Path = PROJECT_ROOT / ".chroma"
    chunk_size: int = 800
    chunk_overlap: int = 100
    table_max_chars: int = 2500

    top_k: int = 6
    briefing_k: int = 4                          # guideline chunks for the standard-of-care section
    min_relevance: float = 0.50
    max_question_chars: int = 1000

    # Emerging-treatment data: the synthetic registry (offline, default) or the live ClinicalTrials.gov API v2
    trials_source: Literal["synthetic", "live"] = "synthetic"
    clinicaltrials_url: str = "https://clinicaltrials.gov/api/v2/studies"
    live_max_trials: int = 40
    http_timeout: float = 20.0

    briefing_cache_hours: float = 24.0                 # reuse a finished briefing (0 = off)
    roles_file: Path = PROJECT_ROOT / "medbrief" / "roles.yaml"
    default_role: str = "strategy_analyst"
    audit_log_path: Path | None = PROJECT_ROOT / "logs" / "audit.jsonl"

    @field_validator("audit_log_path", "bedrock_model_id", "ollama_num_thread", mode="before")
    @classmethod
    def _empty_is_none(cls, v):
        return None if v == "" else v

    @property
    def embedding_model_id(self) -> str:
        return f"bedrock:{self.bedrock_embedding_model_id}" if self.embedding_provider == "bedrock" else f"ollama:{self.ollama_embedding_model}"

    @property
    def index_fingerprint(self) -> str:
        return f"{self.embedding_model_id}|{self.chunk_size}/{self.chunk_overlap}/{self.table_max_chars}|v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
