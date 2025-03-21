# copy source code
FROM alpine:3.20 AS code-layer
WORKDIR /usr/src

COPY src ./src
COPY etc/docker-entrypoint .

FROM python:3.12-slim-bookworm AS service
ARG DEV_DEPS="false"
ARG POETRY_VERSION=1.8.3
ARG PIP_DEFAULT_TIMEOUT=120
WORKDIR /app

COPY pyproject.toml .
COPY poetry.lock .

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3-dev libpq-dev locales cron \
  && pip install poetry==${POETRY_VERSION} \
  && poetry config --local virtualenvs.create false \
	&& if [ "${DEV_DEPS}" = "true" ]; then \
	     echo "=== Install DEV dependencies ===" && \
	     PIP_DEFAULT_TIMEOUT=${PIP_DEFAULT_TIMEOUT} poetry install --no-root --no-cache --no-ansi --no-interaction; \
     else \
       echo "=== Install PROD dependencies ===" && \
       PIP_DEFAULT_TIMEOUT=${PIP_DEFAULT_TIMEOUT} poetry install --only=main --no-root --no-cache --no-ansi --no-interaction;  \
     fi \
  && pip uninstall -y poetry poetry-core poetry-plugin-export \
  && sed -i -e 's/# ru_RU.UTF-8 UTF-8/ru_RU.UTF-8 UTF-8/' /etc/locale.gen && dpkg-reconfigure --frontend=noninteractive locales \
  && apt-get remove python3-dev libpq-dev build-essential -y \
  && apt-get clean \
  && apt-get autoremove -y \
  && rm -rf /var/lib/apt/lists/* \
  && rm -rf /root/.cache/* && rm -rf /root/.config/* && rm -rf /root/.local/*

RUN groupadd --system tg-housing --gid 1005 && \
    useradd --no-log-init --system --gid tg-housing --uid 1005 tg-housing

# Add cron setup (run checking each morning at 6:00 UTC)
# RUN echo "0 6 * * * /usr/local/bin/python /app/src/cli/check_all.py >> /app/.data/cron.log 2>&1" > /etc/cron.d/check-all \
RUN echo "* * * * * APP_SERVICE=check-all /bin/sh /app/docker-entrypoint >> /app/.data/cron.log 2>&1" > /etc/cron.d/check-all \
  && chmod 0644 /etc/cron.d/check-all \
  && crontab /etc/cron.d/check-all

USER tg-housing

COPY --from=code-layer --chown=tg-housing:tg-housing /usr/src .

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

ENTRYPOINT ["/bin/sh", "/app/docker-entrypoint"]
