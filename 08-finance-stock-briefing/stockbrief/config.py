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
    ollama_num_ctx: int = 6144
    ollama_num_thread: int | None = None
    ollama_keep_alive: int = 60
    ollama_num_predict: int = 900
    aws_region: str = "us-east-1"
    bedrock_model_id: str | None = None
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"

    data_dir: Path = PROJECT_ROOT / "data" / "raw"
    cache_dir: Path = PROJECT_ROOT / "data" / "cache"          # live EDGAR / quote downloads (git-ignored)
    chroma_dir: Path = PROJECT_ROOT / ".chroma"
    chunk_size: int = 800
    chunk_overlap: int = 100
    table_max_chars: int = 2500

    top_k: int = 6
    section_k: int = 4                                         # filing chunks per briefing section
    bm25_weight: float = 2.0                                   # BM25 ranking weight in RRF - 2.0 chosen by the RAGAS sweep (F1 0.934 -> 0.986)
    min_relevance: float = 0.45
    max_question_chars: int = 1000

    # Market data and filings: synthetic (offline, fictional NWRB / HLXB) or live (Yahoo Finance chart API + SEC EDGAR)
    data_source: Literal["synthetic", "live"] = "synthetic"
    # SEC requires a descriptive User-Agent with contact details: "Your Company your.name@example.com"
    sec_user_agent: str = ""
    sec_base_url: str = "https://data.sec.gov"
    sec_archive_url: str = "https://www.sec.gov"
    quote_url: str = "https://query1.finance.yahoo.com/v8/finance/chart"
    live_section_chars: int = 15000                            # cap per filing section indexed in live mode (CPU)
    http_timeout: float = 30.0

    briefing_cache_hours: float = 0.5                 # reuse a finished briefing (0 = off)
    roles_file: Path = PROJECT_ROOT / "stockbrief" / "roles.yaml"
    default_role: str = "financial_advisor"
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
