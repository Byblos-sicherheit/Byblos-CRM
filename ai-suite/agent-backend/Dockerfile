FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

COPY requirements.txt pyproject.toml ./
COPY byblos_agent ./byblos_agent
COPY skills ./skills
RUN pip install --no-cache-dir .

RUN mkdir -p /app/runtime/antigravity && chown -R appuser:appuser /app
USER appuser

EXPOSE 3100
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3100/health', timeout=2)"

CMD ["byblos-agent-server"]
