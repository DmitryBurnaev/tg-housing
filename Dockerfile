# copy source code
FROM alpine:3.20 as code-layer
WORKDIR /usr/src

COPY src ./src
COPY etc/docker-entrypoint .

FROM python:3.12-slim-bookworm as service
ARG DEV_DEPS="false"
ARG POETRY_VERSION=1.8.3
ARG PIP_DEFAULT_TIMEOUT=120
WORKDIR /app

COPY pyproject.toml .
COPY poetry.lock .

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3-dev libpq-dev  \
  && pip install poetry==${POETRY_VERSION} \
  && poetry config --local virtualenvs.create false \
	&& if [ "${DEV_DEPS}" = "true" ]; then \
	     echo "=== Install DEV dependencies ===" && \
	     PIP_DEFAULT_TIMEOUT=${PIP_DEFAULT_TIMEOUT} poetry install --only=main --no-root --no-cache --no-ansi --no-interaction; \
     else \
       echo "=== Install PROD dependencies ===" && \
       PIP_DEFAULT_TIMEOUT=${PIP_DEFAULT_TIMEOUT} poetry install --no-root --no-cache --no-ansi --no-interaction;  \
     fi \
  && pip uninstall -y poetry poetry-core poetry-plugin-export \
  && apt-get remove python3-dev libpq-dev build-essential -y \
  && apt-get clean \
  && apt-get autoremove -y \
  && rm -rf /var/lib/apt/lists/* \
  && rm -rf /root/.cache/* && rm -rf /root/.config/* && rm -rf /root/.local/*

RUN groupadd --system tg_housing --gid 1005 && \
    useradd --no-log-init --system --gid tg_housing --uid 1005 tg_housing
USER tg_housing

COPY --from=code-layer --chown=tg_housing:tg_housing /usr/src .

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["/bin/sh", "/app/docker-entrypoint"]
