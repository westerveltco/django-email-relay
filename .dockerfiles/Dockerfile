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


FROM base as builder
RUN --mount=type=cache,target=/root/.cache
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project
COPY . /src
WORKDIR /src
RUN --mount=type=cache,target=/root/.cache \
    uv sync --locked --no-dev --no-editable


FROM base as final
RUN mkdir -p /app
COPY --from=builder /app /app
RUN addgroup --system django \
  && adduser --system --ingroup django django \
  && chown -R django:django /app
USER django
WORKDIR /app
CMD ["uv", "run", "-m", "service"]
