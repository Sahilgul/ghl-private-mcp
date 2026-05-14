FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir -e .

# Cloud Run injects $PORT at runtime (default 8080)
ENV PORT=8080

CMD python -m ghl_mcp.server --transport http --host 0.0.0.0 --port $PORT
