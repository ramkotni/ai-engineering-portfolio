# PlantAssist container - used for both ECS/App Runner (FastAPI) and AgentCore Runtime.
# AgentCore requires linux/arm64:  docker buildx build --platform linux/arm64 ...
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    LLM_PROVIDER=bedrock \
    EMBEDDING_PROVIDER=bedrock \
    CHROMA_DIR=/tmp/chroma

COPY requirements-app.txt .
RUN pip install --no-cache-dir -r requirements-app.txt

COPY plant_assist/ plant_assist/
COPY data/ data/
COPY agentcore_app.py .

EXPOSE 8000 8080
# Default: REST API. For AgentCore override the command with: python agentcore_app.py
CMD ["uvicorn", "plant_assist.api:app", "--host", "0.0.0.0", "--port", "8000"]
