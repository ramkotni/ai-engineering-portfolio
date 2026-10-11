FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY feasibility/ feasibility/
COPY data/ data/
COPY models/ models/
ENV OLLAMA_BASE_URL=http://host.docker.internal:11434
EXPOSE 8004
CMD ["uvicorn", "feasibility.api:app", "--host", "0.0.0.0", "--port", "8004"]
