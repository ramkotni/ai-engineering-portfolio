"""Model provider factory: swap Ollama <-> Amazon Bedrock with one env var."""
from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from app.config import Settings, get_settings


def get_chat_model(
    settings: Settings | None = None,
    *,
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
) -> BaseChatModel:
    s = settings or get_settings()
    provider = provider or s.llm_provider
    temperature = s.llm_temperature if temperature is None else temperature

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model or s.ollama_chat_model,
            base_url=s.ollama_base_url,
            temperature=temperature,
            num_ctx=s.ollama_num_ctx,
            num_predict=s.llm_max_tokens,
            client_kwargs={"timeout": s.llm_timeout_s},
        )

    if provider == "bedrock":
        from botocore.config import Config
        from langchain_aws import ChatBedrockConverse

        return ChatBedrockConverse(
            model=model or s.bedrock_chat_model_id,
            region_name=s.aws_region,
            temperature=temperature,
            max_tokens=s.llm_max_tokens,
            config=Config(
                read_timeout=s.llm_timeout_s,
                retries={"max_attempts": 4, "mode": "adaptive"},
            ),
        )

    raise ValueError(f"Unknown LLM provider: {provider}")


def get_judge_model(settings: Settings | None = None) -> BaseChatModel:
    """LLM-as-judge for evaluation. Ideally a stronger model than the one under test."""
    s = settings or get_settings()
    return get_chat_model(s, provider=s.eval_judge_provider, model=s.eval_judge_model, temperature=0.0)


def get_embeddings(settings: Settings | None = None) -> Embeddings:
    s = settings or get_settings()
    provider = s.effective_embeddings_provider

    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(model=s.ollama_embed_model, base_url=s.ollama_base_url)

    if provider == "bedrock":
        from langchain_aws import BedrockEmbeddings

        return BedrockEmbeddings(model_id=s.bedrock_embed_model_id, region_name=s.aws_region)

    raise ValueError(f"Unknown embeddings provider: {provider}")
