FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# RDKit + pypdf wheels need build tooling and a few system libs
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libxrender1 \
        libxext6 \
        libsm6 \
        libgl1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app

RUN mkdir -p /data/chroma /data/uploads

EXPOSE 8000

# Single worker keeps in-process Chroma + MCP servers consistent. Scale by
# replicating containers behind a load balancer, not by adding workers.
# Shell form so $PORT (injected by Render/Railway/Fly) is honoured. Defaults
# to 8000 for local docker-compose.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
