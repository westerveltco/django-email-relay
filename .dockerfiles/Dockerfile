FROM python:3.13-slim as base
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV UV_LINK_MODE copy
ENV UV_COMPILE_BYTECODE 1
ENV UV_PYTHON_DOWNLOADS never
ENV UV_PYTHON /usr/local/bin/python
ENV UV_PROJECT_ENVIRONMENT /app
ENV PATH /app/bin:$PATH
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN mkdir -p /app
WORKDIR /app


FROM base as builder
COPY pyproject.toml uv.lock* ./
RUN uv sync --locked --no-dev --no-install-project
COPY src /app/src
COPY LICENSE README.md ./
RUN uv sync --locked --no-dev --no-editable


FROM base as final
COPY --from=builder /app /app
RUN addgroup --system django \
  && adduser --system --ingroup django django \
  && chown -R django:django /app
USER django
CMD ["uv", "run", "-m", "service"]
