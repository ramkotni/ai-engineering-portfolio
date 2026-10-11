FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY payops/ payops/
COPY data/ data/
ENV OLLAMA_BASE_URL=http://host.docker.internal:11434
EXPOSE 8001
CMD ["uvicorn", "payops.api:app", "--host", "0.0.0.0", "--port", "8001"]
