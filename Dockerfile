# copy source code
FROM alpine:3.20 AS code-layer
WORKDIR /usr/src

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini .
COPY etc/docker-entrypoint .
COPY etc/docker-crontab .

FROM python:3.12-slim-bookworm AS service
ARG DEV_DEPS="false"
ARG POETRY_VERSION=1.8.3
ARG PIP_DEFAULT_TIMEOUT=120
ARG CRONTAB_RECORD="0 6 * * *"
WORKDIR /app

COPY pyproject.toml .
COPY poetry.lock .

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3-dev locales cron \
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
  && apt-get remove python3-dev build-essential -y \
  && apt-get clean \
  && apt-get autoremove -y \
  && rm -rf /var/lib/apt/lists/* \
  && rm -rf /root/.cache/* && rm -rf /root/.config/* && rm -rf /root/.local/*

RUN groupadd --system tg-housing --gid 1005 && \
    useradd --no-log-init --system --gid tg-housing --uid 1005 tg-housing

# Crontab: pre-setup
ENV CRONTAB_FILE=/etc/cron.d/check-all
ENV CRONTAB_ENVFILE=/app/container.env
ENV CRONTAB_PIDFILE=/var/run/crond.pid
ENV CRONTAB_RECORD=${CRONTAB_RECORD}
ENV CRONTAB_LOGFILE=/app/.data/cron.log

# Add cron setup (run checking each morning at 6:00 UTC)
RUN echo "SHELL=/bin/bash" >> ${CRONTAB_FILE} && \
    echo "BASH_ENV=${CRONTAB_ENVFILE}" >> ${CRONTAB_FILE} && \
    echo "${CRONTAB_RECORD} /usr/local/bin/python -m src.cli.check_all >> ${CRONTAB_LOGFILE} 2>&1" >> ${CRONTAB_FILE} && \
    chmod 0640 ${CRONTAB_FILE} && \
    crontab ${CRONTAB_FILE} && \
    touch ${CRONTAB_ENVFILE} && \
    chmod 0640 ${CRONTAB_ENVFILE} && \
    chown tg-housing:tg-housing ${CRONTAB_ENVFILE} && \
    touch ${CRONTAB_PIDFILE} && \
    chown tg-housing:tg-housing ${CRONTAB_PIDFILE} && \
    chmod gu+s /usr/sbin/cron

USER tg-housing

COPY --from=code-layer --chown=tg-housing:tg-housing /usr/src .

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

ENTRYPOINT ["/bin/sh", "/app/docker-entrypoint"]
