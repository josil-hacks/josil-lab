FROM ghcr.io/astral-sh/uv:0.12.17 AS uv

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Keep uv in the image so the locked environment can be installed reproducibly.
COPY --from=uv /uv /uvx /bin/

# Install dependencies before application code to preserve the Docker cache.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "contact_form.main:app", "--host", "0.0.0.0", "--port", "8000"]
