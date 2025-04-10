ARG PYTHON_VERSION=3.13
ARG UID=1000
ARG GID=1000

FROM python:${PYTHON_VERSION}-slim as base
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV UV_LINK_MODE copy
ENV UV_COMPILE_BYTECODE 1
ENV UV_PYTHON_DOWNLOADS never
ENV UV_PYTHON python${PYTHON_VERSION}
ENV UV_PROJECT_ENVIRONMENT /app
ENV PATH /app/bin:$PATH
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv


FROM base as builder
RUN --mount=type=cache,target=/root/.cache \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project
COPY . /src
WORKDIR /src
RUN --mount=type=cache,target=/root/.cache \
    uv sync --locked --no-dev --no-editable --extra hc --extra psycopg --extra relay


FROM base as final
ARG UID
ARG GID
RUN mkdir -p /app
COPY --from=builder /app /app
RUN addgroup -gid "${GID}" --system django \
  && adduser -uid "${UID}" -gid "${GID}" --home /home/django --system django \
  && chown -R django:django /app
USER django
WORKDIR /app
CMD ["uv", "run", "-m", "email_relay.service"]
