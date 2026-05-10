FROM python:3.11-slim

ARG USE_SEMANTIC_EMBEDDINGS=false

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "$USE_SEMANTIC_EMBEDDINGS" = "true" ]; then \
        pip install --no-cache-dir -r requirements-ml.txt; \
    fi

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
