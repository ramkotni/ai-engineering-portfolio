# Multi-arch image. AgentCore Runtime requires linux/arm64:
#   docker buildx build --platform linux/arm64 -t evergreen-assist .
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app
COPY data ./data
# Pre-built vector index: run `python -m app.ingest --reset` with the target
# embeddings provider BEFORE `docker build` (deploy.sh does this). Baking the
# index in keeps cold starts fast and avoids re-embedding on every session.
COPY chroma_db ./chroma_db

RUN useradd --create-home --uid 1000 appuser && chown -R appuser /app
USER appuser

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/ping').status==200 else 1)"

CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
