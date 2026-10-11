FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY supplykb/ supplykb/
COPY data/ data/
ENV OLLAMA_BASE_URL=http://host.docker.internal:11434
EXPOSE 8003
CMD ["uvicorn", "supplykb.api:app", "--host", "0.0.0.0", "--port", "8003"]
