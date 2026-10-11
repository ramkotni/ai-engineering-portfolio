"""Runtime configuration, loaded from environment variables and an optional .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Model providers -------------------------------------------------
    llm_provider: Literal["ollama", "bedrock"] = "ollama"
    embedding_provider: Literal["ollama", "bedrock"] = "ollama"
    temperature: float = 0.0

    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2"
    ollama_embedding_model: str = "nomic-embed-text"
    # Resource controls for CPU-only machines. The RAG prompt (6 excerpts) is ~2.5k tokens,
    # so 4096 is enough; each doubling of num_ctx roughly doubles the model's KV-cache memory.
    ollama_num_ctx: int = 4096
    ollama_num_thread: int | None = None  # cap CPU cores used for inference (None = all cores)
    ollama_keep_alive: int = 60           # seconds to keep the model in RAM after the last call (0 = unload immediately)
    ollama_num_predict: int = 512         # max answer tokens - bounds generation time

    aws_region: str = "us-east-1"
    # Claude model ID or inference-profile ID enabled in your Bedrock account,
    # e.g. the value shown by `aws bedrock list-inference-profiles`.
    bedrock_model_id: str | None = None
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"

    # --- Knowledge base --------------------------------------------------
    docs_dir: Path = PROJECT_ROOT / "data" / "docs"
    chroma_dir: Path = PROJECT_ROOT / ".chroma"
    # Chunk sizes are in characters (~4 chars per token). 900 chars ~ 225 tokens: one procedure
    # section or a few steps - small enough to be specific, large enough to keep steps together.
    chunk_size: int = 900
    chunk_overlap: int = 120          # only used when a single paragraph exceeds chunk_size
    table_max_chars: int = 2500       # tables up to this size stay in one chunk; larger ones split by rows

    # --- Retrieval & graph behaviour --------------------------------------
    top_k: int = 8                       # chunks fetched per routed source (RAGAS sweep: recall 0.70 -> 0.84 vs k=5; prompt still capped by max_context_chunks)
    policy_top_k: int = 2                # chunks fetched for sources added by safety policy
    max_context_chunks: int = 6          # chunks passed to the generator
    min_relevance: float = 0.55          # cosine-similarity floor for a chunk to count as relevant
    route_confidence_threshold: float = 0.6  # below this, search every source
    max_query_rewrites: int = 1
    grounding_check: bool = True         # LLM verifier (second pass)
    max_generation_attempts: int = 2

    # --- Guardrails -------------------------------------------------------
    max_question_chars: int = 1000
    numeric_grounding_check: bool = True  # every number in the answer must appear in the excerpts
    # Optional Amazon Bedrock Guardrail applied to every Bedrock call (content filters, denied topics, PII).
    bedrock_guardrail_id: str | None = None
    bedrock_guardrail_version: str = "DRAFT"

    # --- Observability ----------------------------------------------------
    audit_log_path: Path | None = PROJECT_ROOT / "logs" / "audit.jsonl"  # local Q&A audit trail; empty = off

    # --- Roles ---------------------------------------------------------------
    roles_file: Path = PROJECT_ROOT / "plant_assist" / "roles.yaml"
    default_role: str = "floor_supervisor"

    @field_validator("audit_log_path", "bedrock_guardrail_id", "bedrock_model_id", mode="before")
    @classmethod
    def _empty_is_none(cls, v):
        return None if v == "" else v

    @property
    def embedding_model_id(self) -> str:
        if self.embedding_provider == "bedrock":
            return f"bedrock:{self.bedrock_embedding_model_id}"
        return f"ollama:{self.ollama_embedding_model}"

    @property
    def index_fingerprint(self) -> str:
        """Changes whenever the embedding model or chunking would produce a different index."""
        from plant_assist.chunking import CHUNKER_VERSION

        return f"{self.embedding_model_id}|chunker{CHUNKER_VERSION}|{self.chunk_size}/{self.chunk_overlap}/{self.table_max_chars}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
