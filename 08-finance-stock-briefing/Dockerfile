FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY stockbrief/ stockbrief/
COPY data/raw/ data/raw/
ENV OLLAMA_BASE_URL=http://host.docker.internal:11434
EXPOSE 8008
CMD ["uvicorn", "stockbrief.api:app", "--host", "0.0.0.0", "--port", "8008"]
