FROM python:3.9 as requirements-stage

WORKDIR /tmp

COPY ./pyproject.toml ./poetry.lock* /tmp/

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py -o install-poetry.py

RUN python install-poetry.py --yes

ENV PATH="${PATH}:/root/.local/bin"

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9-slim

ENV TZ Asia/Shanghai
ENV SENTRY_RELEASE=version

WORKDIR /app

COPY --from=requirements-stage /tmp/requirements.txt /app/requirements.txt

RUN apt-get update \
    && apt-get install -y fonts-noto \
    && sudo locale-gen zh_CN zh_CN.UTF-8 \
    && sudo update-locale LC_ALL=zh_CN.UTF-8 LANG=zh_CN.UTF-8 \
    && fc-cache -fv \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade -r requirements.txt

RUN rm requirements.txt

COPY bot.py pyproject.toml /app/
COPY src /app/src/
