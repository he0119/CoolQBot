FROM python:3.9 as requirements-stage

WORKDIR /tmp

COPY ./pyproject.toml ./poetry.lock* /tmp/

RUN curl -sSL https://install.python-poetry.org | python3 -

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

WORKDIR /app

ENV SENTRY_RELEASE=version

ENV LANG zh_CN.UTF-8
ENV LANGUAGE zh_CN.UTF-8
ENV LC_ALL zh_CN.UTF-8
ENV TZ Asia/Shanghai
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y locales locales-all fonts-noto

RUN apt-get update && \
  && apt-get install -y --no-install-recommends git \
  && apt-get purge -y --auto-remove \
  rm -rf /var/lib/apt/lists/*

COPY --from=requirements-stage /tmp/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r requirements.txt

RUN echo "Install playwright headless browser..." \
  && playwright install chromium \
  && apt-get install -y libnss3-dev libxss1 libasound2 libxrandr2\
  libatk1.0-0 libgtk-3-0 libgbm-dev libxshmfence1

COPY bot.py /app/
COPY src /app/src/
