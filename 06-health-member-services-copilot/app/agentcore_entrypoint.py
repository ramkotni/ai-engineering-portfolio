"""Alternative entrypoint using the Bedrock AgentCore Python SDK.

Use this with the AgentCore starter toolkit:
    agentcore configure --entrypoint app/agentcore_entrypoint.py
    agentcore launch
    agentcore invoke '{"prompt": "What is the Gold PPO deductible?", "member_id": "M1001"}'

(The FastAPI app in app/api.py implements the same /invocations + /ping
contract for bring-your-own-container deployments.)
"""
from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from app.config import get_settings
from app.logging_config import setup_logging
from app.service import AgentService, ChatRequest

setup_logging(get_settings().log_level)
app = BedrockAgentCoreApp()
service = AgentService.from_settings()


@app.entrypoint
def invoke(payload: dict, context=None) -> dict:
    session_id = getattr(context, "session_id", None) or payload.get("session_id")
    req = ChatRequest(
        question=payload.get("prompt", ""),
        session_id=session_id,
        member_id=payload.get("member_id"),
    )
    return service.ask(req).model_dump()


if __name__ == "__main__":
    app.run()
