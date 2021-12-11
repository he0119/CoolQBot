FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9-slim

ENV TZ=Asia/Shanghai

ENV SENTRY_RELEASE=version

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get purge -y --auto-remove && \
    rm -rf /var/lib/apt/lists/*

COPY ./pyproject.toml ./poetry.lock /app/
RUN set -ex; \
    python3 -m pip install poetry; \
    poetry config virtualenvs.create false; \
    poetry install --no-root --no-dev;

COPY bot.py /app/
COPY src /app/src/
