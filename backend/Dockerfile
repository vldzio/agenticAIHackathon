# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Application code, trained model artifacts and the small evaluation set (used by /models/evaluation).
# Training data is deliberately excluded (see .dockerignore); retrain with `make train`.
COPY app ./app
# ml_pipeline is imported by the live evaluation endpoint (shared cleaning code)
COPY ml_pipeline ./ml_pipeline
COPY scripts ./scripts
COPY artifacts ./artifacts
COPY data/evaluation_dataset ./data/evaluation_dataset

RUN useradd --create-home --uid 10001 aetherfit && mkdir -p /data && chown aetherfit /data
USER aetherfit

ENV AETHERFIT_ENV=prod \
    AETHERFIT_DATABASE_URL=sqlite:////data/aetherfit.db

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status == 200 else 1)"

# One worker on purpose: the rate limiter is in-process. Scale out behind a shared limiter if needed.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
