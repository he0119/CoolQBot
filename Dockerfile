FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

ENV LANG zh_CN.UTF-8
ENV LANGUAGE zh_CN.UTF-8
ENV LC_ALL zh_CN.UTF-8
ENV TZ Asia/Shanghai
ENV DEBIAN_FRONTEND noninteractive

ENV SENTRY_RELEASE=version

# 安装浏览器依赖，字体
RUN set -ex; \
  apt-get update; \
  apt-get install -y locales locales-all fonts-noto; \
  apt-get install -y libnss3-dev libxss1 libasound2 libxrandr2 \
  libatk1.0-0 libgtk-3-0 libgbm-dev libxshmfence1;

COPY ./pyproject.toml ./poetry.lock /app/
RUN set -ex; \
  curl -sSL https://install.python-poetry.org | python3 -; \
  $HOME/.local/bin/poetry config virtualenvs.create false; \
  $HOME/.local/bin/poetry install --no-root --no-dev;

RUN echo "Install playwright headless browser..." \
  && playwright install chromium

COPY bot.py /app/
COPY src /app/src/
