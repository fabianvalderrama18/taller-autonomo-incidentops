FROM ghcr.io/astral-sh/uv:0.13.9 AS uv
FROM python:3.12-slim
COPY --from=uv /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH"
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY data ./data
RUN useradd --create-home incidentops
USER incidentops
EXPOSE 8000
CMD ["uvicorn", "src.adapters.inbound.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
