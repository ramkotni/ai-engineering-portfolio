"""Centralised, environment-driven configuration.

Every runtime decision (local vs. AWS, which model, which vector store, which
guardrails) is controlled here so the *same code* runs on a laptop with Ollama
and in AWS Bedrock AgentCore with Claude + Titan.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Environment ---
    app_env: Literal["local", "aws"] = "local"
    log_level: str = "INFO"

    # --- Model providers ---
    llm_provider: Literal["ollama", "bedrock"] = "ollama"
    embeddings_provider: Literal["ollama", "bedrock"] | None = None  # defaults to llm_provider

    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_num_ctx: int = 8192

    aws_region: str = "us-east-1"
    # Use the newest Claude inference profile enabled in your account/region.
    bedrock_chat_model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    bedrock_embed_model_id: str = "amazon.titan-embed-text-v2:0"

    # Optional separate (stronger) judge model for offline evaluation.
    eval_judge_provider: Literal["ollama", "bedrock"] | None = None
    eval_judge_model: str | None = None

    llm_temperature: float = 0.0
    llm_max_tokens: int = 1024
    llm_timeout_s: int = 120

    # --- Retrieval ---
    vector_backend: Literal["chroma", "bedrock_kb"] = "chroma"
    chroma_persist_dir: Path = PROJECT_ROOT / "chroma_db"
    chroma_collection: str = "policy_docs"
    bedrock_kb_id: str | None = None
    docs_dir: Path = PROJECT_ROOT / "data" / "policies"
    claims_file: Path = PROJECT_ROOT / "data" / "claims" / "claims.json"
    chunk_size: int = 900
    chunk_overlap: int = 120
    retrieval_k: int = 4
    relevance_threshold: float = 0.50  # calibrated for nomic-embed-text; re-tune per embedding model
    auto_ingest: bool = True  # build the index on startup if it is empty

    # --- Agent behaviour ---
    enable_doc_grading: bool = True
    enable_groundedness_check: bool = True
    # numeric = deterministic $/% check; llm = LLM fact-checker; both = numeric then llm.
    # Eval showed the 3B local model is an unreliable critic, so 'both' is meant for Bedrock Claude.
    groundedness_mode: Literal["numeric", "llm", "both"] = "numeric"
    max_query_rewrites: int = 1
    max_regenerations: int = 1
    history_window: int = 6  # messages of history passed to the supervisor

    # --- Memory ---
    checkpointer: Literal["memory", "sqlite"] = "memory"
    sqlite_path: Path = PROJECT_ROOT / "checkpoints.db"

    # --- Guardrails ---
    max_input_chars: int = 2000
    bedrock_guardrail_id: str | None = None
    bedrock_guardrail_version: str = "DRAFT"
    guardrail_fail_closed: bool = True  # block if the managed guardrail is unreachable
    # Official contact details that must never be redacted from answers.
    pii_allowlist: list[str] = [
        "1-800-555-0142", "1-800-555-0199", "1-800-555-0177", "privacy@evergreenhealth.example",
    ]

    # --- Observability: LangSmith (off unless LANGSMITH_TRACING=true and LANGSMITH_API_KEY set) ---
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "evergreen-member-assist"
    langsmith_endpoint: str | None = None  # e.g. https://eu.api.smith.langchain.com or a self-hosted URL
    langsmith_auto_feedback: bool = True  # attach grounded / guardrail scores to every trace
    langsmith_hide_inputs: bool = False  # strict PHI policy: send no run inputs/outputs to LangSmith
    langsmith_hide_outputs: bool = False
    app_version: str = "1.0.0"

    # --- API ---
    api_key: str | None = Field(default=None, description="If set, /chat requires header x-api-key")
    port: int = 8080

    @property
    def effective_embeddings_provider(self) -> str:
        return self.embeddings_provider or self.llm_provider

    @property
    def collection_name(self) -> str:
        # Embedding dimensions differ per provider (nomic=768, titan v2=1024),
        # so each provider gets its own collection.
        return f"{self.chroma_collection}_{self.effective_embeddings_provider}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
