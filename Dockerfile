FROM python:3.12-slim

WORKDIR /app

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --no-create-home appuser

COPY pyproject.toml ./

RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache -r pyproject.toml

RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app/logs /app/data

USER appuser

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
  CMD test -f /app/data/invoices.db || exit 1

CMD ["python", "-m", "app.main"]
