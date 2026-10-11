"""Settings from environment variables / .env (never committed - see .env.example)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    # --- Models -----------------------------------------------------------
    llm_provider: Literal["ollama", "bedrock"] = "ollama"
    embedding_provider: Literal["ollama", "bedrock"] = "ollama"
    temperature: float = 0.0
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_num_ctx: int = 4096
    ollama_num_thread: int | None = None
    ollama_keep_alive: int = 60
    ollama_num_predict: int = 512
    aws_region: str = "us-east-1"
    bedrock_model_id: str | None = None
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"

    # --- Data / index ------------------------------------------------------
    data_dir: Path = PROJECT_ROOT / "data" / "raw"
    chroma_dir: Path = PROJECT_ROOT / ".chroma"
    chunk_size: int = 700              # characters, for the troubleshooting guide
    chunk_overlap: int = 100
    table_max_chars: int = 2500

    # --- Agents ------------------------------------------------------------
    search_top_k: int = 10             # similar events per question (RAGAS sweep: recall 0.85 -> 1.0 vs k=6)
    knowledge_top_k: int = 3           # guide chunks retrieved per question
    min_relevance: float = 0.50        # cosine floor
    intent_confidence_threshold: float = 0.55

    # --- Guardrails / roles / monitoring ----------------------------------
    max_question_chars: int = 1000
    roles_file: Path = PROJECT_ROOT / "fleetops" / "roles.yaml"
    default_role: str = "fleet_manager"
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
