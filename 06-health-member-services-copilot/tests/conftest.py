"""Test fixtures: a deterministic fake LLM + in-memory KB so the graph can be
tested in CI with no Ollama / AWS dependency."""
from __future__ import annotations

import json
from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app import prompts
from app.config import PROJECT_ROOT, Settings
from app.graph.nodes import Deps
from app.guardrails import Guardrails
from app.service import AgentService
from app.tools import ClaimsRepository
from app.vectorstore import RetrievedChunk


class RuleBasedFakeLLM(BaseChatModel):
    """Dispatches on the system prompt so every node gets a plausible reply."""

    grounded: bool = True

    @property
    def _llm_type(self) -> str:
        return "fake-rule-based"

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs: Any) -> ChatResult:
        system = str(messages[0].content)
        user = str(messages[-1].content)
        if system == prompts.SUPERVISOR_SYSTEM:
            latest = user.split("Latest member message:")[-1].lower()
            if "clm-" in latest or "my claim" in latest:
                out = {"intent": "claim_status", "standalone_question": latest.strip(), "claim_id": None}
            elif any(w in latest for w in ("hello", "hi ", "thanks")):
                out = {"intent": "greeting", "standalone_question": latest.strip(), "claim_id": None}
            elif "stock" in latest or "diagnose" in latest:
                out = {"intent": "out_of_scope", "standalone_question": latest.strip(), "claim_id": None}
            else:
                out = {"intent": "policy_question", "standalone_question": latest.strip(), "claim_id": None}
            text = json.dumps(out)
        elif system == prompts.GRADER_SYSTEM:
            text = json.dumps({"relevant_ids": [1]})
        elif system == prompts.REWRITE_SYSTEM:
            text = json.dumps({"query": user + " policy"})
        elif system == prompts.GROUNDEDNESS_SYSTEM:
            text = json.dumps({"grounded": self.grounded, "unsupported_claims": []})
        else:
            text = "The in-network deductible is $500 individual [1]. Call 1-800-555-0142. Contact me at bob@example.com"
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])


class FakeKB:
    def __init__(self, chunks: list[RetrievedChunk] | None = None):
        self.chunks = chunks if chunks is not None else [
            RetrievedChunk(
                content="Evergreen Gold PPO > Deductibles\nIn-network deductible: $500 individual. Member Services 1-800-555-0142.",
                source="01_gold_ppo_benefits.md", section="Deductibles", score=0.8,
            )
        ]
        self.queries: list[str] = []

    def search(self, query: str, k: int):
        self.queries.append(query)
        return self.chunks[:k]

    def count(self) -> int:
        return len(self.chunks)


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, llm_provider="ollama", bedrock_guardrail_id=None, api_key=None)


def make_service(settings: Settings, llm=None, kb=None) -> AgentService:
    deps = Deps(
        llm=llm or RuleBasedFakeLLM(),
        kb=kb or FakeKB(),
        claims=ClaimsRepository(PROJECT_ROOT / "data" / "claims" / "claims.json"),
        guardrails=Guardrails(settings),
        settings=settings,
    )
    return AgentService(settings, deps)


@pytest.fixture
def service(settings) -> AgentService:
    return make_service(settings)
