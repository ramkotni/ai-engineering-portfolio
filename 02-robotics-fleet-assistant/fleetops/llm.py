"""Model factories: Ollama locally, Amazon Bedrock in AWS - selected by configuration only."""

from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from fleetops.config import get_settings


@lru_cache
def get_chat_model() -> BaseChatModel:
    s = get_settings()
    if s.llm_provider == "bedrock":
        from langchain_aws import ChatBedrockConverse

        if not s.bedrock_model_id:
            raise ValueError("BEDROCK_MODEL_ID must be set when LLM_PROVIDER=bedrock")
        return ChatBedrockConverse(model=s.bedrock_model_id, region_name=s.aws_region, temperature=s.temperature)

    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=s.ollama_chat_model, base_url=s.ollama_base_url, temperature=s.temperature,
        num_ctx=s.ollama_num_ctx, num_thread=s.ollama_num_thread, num_predict=s.ollama_num_predict,
        keep_alive=s.ollama_keep_alive,
    )


@lru_cache
def get_embeddings() -> Embeddings:
    s = get_settings()
    if s.embedding_provider == "bedrock":
        from langchain_aws import BedrockEmbeddings

        return BedrockEmbeddings(model_id=s.bedrock_embedding_model_id, region_name=s.aws_region)

    from langchain_ollama import OllamaEmbeddings

    inner = OllamaEmbeddings(model=s.ollama_embedding_model, base_url=s.ollama_base_url,
                             num_thread=s.ollama_num_thread, keep_alive=s.ollama_keep_alive)
    # nomic-embed-text is trained with task prefixes; without them retrieval quality drops.
    return PrefixedEmbeddings(inner, "search_document: ", "search_query: ") if "nomic" in s.ollama_embedding_model else inner


class PrefixedEmbeddings(Embeddings):
    def __init__(self, inner: Embeddings, document_prefix: str, query_prefix: str):
        self.inner, self.document_prefix, self.query_prefix = inner, document_prefix, query_prefix

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.inner.embed_documents([self.document_prefix + t for t in texts])

    def embed_query(self, text: str) -> list[float]:
        return self.inner.embed_query(self.query_prefix + text)


def structured(llm: BaseChatModel, schema):
    """JSON-schema constrained decoding on Ollama; tool calling on Bedrock/Claude."""
    method = "json_schema" if type(llm).__name__ == "ChatOllama" else "function_calling"
    return llm.with_structured_output(schema, method=method)
