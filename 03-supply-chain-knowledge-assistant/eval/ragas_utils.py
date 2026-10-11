"""RAGAS helpers shared by ragas_eval.py.

- Compatibility shim: ragas 0.4.3 imports ChatVertexAI from langchain_community.chat_models.vertexai,
  which langchain-community 0.4 (the LangChain 1.x line) removed. We register a stub module so ragas
  imports cleanly; Vertex AI is not used here.
- Judge LLM: Ollama through its OpenAI-compatible endpoint (http://localhost:11434/v1), or any OpenAI
  key if RAGAS_JUDGE_PROVIDER=openai.
"""

import asyncio
import os
import sys
import types
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
if "langchain_community.chat_models.vertexai" not in sys.modules:
    try:
        import langchain_community.chat_models.vertexai  # noqa: F401
    except ImportError:
        _stub = types.ModuleType("langchain_community.chat_models.vertexai")
        _stub.ChatVertexAI = type("ChatVertexAI", (), {})
        sys.modules["langchain_community.chat_models.vertexai"] = _stub

from ragas.dataset_schema import SingleTurnSample
from ragas.metrics._context_precision import NonLLMContextPrecisionWithReference
from ragas.metrics._context_recall import NonLLMContextRecall
from ragas.metrics.collections import RougeScore


def non_llm_scores(question: str, retrieved: list[str], reference_contexts: list[str],
                   response: str | None = None, reference: str | None = None) -> dict:
    """Retrieval quality without any LLM: string-similarity based context precision / recall (+ ROUGE-L)."""
    sample = SingleTurnSample(user_input=question, retrieved_contexts=retrieved or [""],
                              reference_contexts=reference_contexts or [""])
    out = {
        "context_precision": round(NonLLMContextPrecisionWithReference().single_turn_score(sample), 3),
        "context_recall": round(NonLLMContextRecall().single_turn_score(sample), 3),
    }
    if response and reference:
        out["rouge_l"] = round(float(RougeScore().score(reference=reference, response=response).value), 3)
    return out


def judge_llm():
    """RAGAS judge. Default: local Ollama model via the OpenAI-compatible API (no cost, slow on CPU)."""
    from openai import AsyncOpenAI
    from ragas.llms import llm_factory

    if os.getenv("RAGAS_JUDGE_PROVIDER", "ollama") == "openai":
        return llm_factory(os.getenv("RAGAS_JUDGE_MODEL", "gpt-4o-mini"), client=AsyncOpenAI())
    host = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    client = AsyncOpenAI(base_url=host + "/v1", api_key="ollama")
    return llm_factory(os.getenv("RAGAS_JUDGE_MODEL") or _default_judge(host), provider="openai", client=client,
                       temperature=0, max_tokens=1024)


def _default_judge(host: str) -> str:
    """Prefer the CPU-capped judge (tools/ollama/Modelfile.judge): the OpenAI-compatible endpoint cannot pass
    num_thread, so without it the judge would use every core."""
    import httpx

    try:
        names = {m["name"].split(":")[0] for m in httpx.get(host + "/api/tags", timeout=5).json()["models"]}
    except Exception:  # noqa: BLE001
        names = set()
    return "llama3.2-judge" if "llama3.2-judge" in names else "llama3.2"


def llm_scores(llm, question: str, response: str, retrieved: list[str], reference: str) -> dict:
    """LLM-judged metrics: faithfulness and response groundedness (answer supported by contexts) and context recall
    (contexts cover the reference). Small local judges often fail faithfulness's structured output - errors are recorded."""
    from ragas.metrics.collections import ContextRecall, Faithfulness, ResponseGroundedness

    timeout = float(os.getenv("RAGAS_JUDGE_TIMEOUT", "600"))

    async def run() -> dict:
        out = {}
        for name, coro in (("faithfulness", Faithfulness(llm=llm).ascore(user_input=question, response=response,
                                                                             retrieved_contexts=retrieved)),
                           ("llm_context_recall", ContextRecall(llm=llm).ascore(user_input=question, retrieved_contexts=retrieved,
                                                                                reference=reference)),
                           # Simpler 0-2 rating prompt: more robust than faithfulness with small local judges.
                           ("response_groundedness", ResponseGroundedness(llm=llm).ascore(response=response,
                                                                                          retrieved_contexts=retrieved))):
            try:
                out[name] = round(float((await asyncio.wait_for(coro, timeout)).value), 3)
            except Exception as exc:  # noqa: BLE001 - small local judges sometimes return malformed JSON
                out[name] = None
                out[f"{name}_error"] = type(exc).__name__
        return out

    return asyncio.run(run())
