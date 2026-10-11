"""Amazon Bedrock AgentCore Runtime entrypoint.

AgentCore runs this container and forwards POST /invocations payloads to `invoke`.
Set LLM_PROVIDER=bedrock and EMBEDDING_PROVIDER=bedrock in the runtime environment.
Local smoke test:
    python agentcore_app.py
    curl -X POST localhost:8080/invocations -H "Content-Type: application/json" -d '{"prompt": "When is FAI required?"}'
"""

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from plant_assist.ingest import ensure_index
from plant_assist.service import get_assistant

app = BedrockAgentCoreApp()
ensure_index()  # small corpus: index is built at container start (Titan embeddings)


@app.entrypoint
def invoke(payload: dict) -> dict:
    question = payload.get("prompt") or payload.get("question") or ""
    if not question.strip():
        return {"error": "payload must include 'prompt'"}
    return get_assistant().ask(question)


if __name__ == "__main__":
    app.run()
