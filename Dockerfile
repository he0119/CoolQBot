FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

ENV TZ=Asia/Shanghai

ENV SENTRY_RELEASE=version

COPY ./pyproject.toml ./poetry.lock /app/
RUN set -ex; \
  curl -sSL https://install.python-poetry.org | python3 -; \
  $HOME/.local/bin/poetry config virtualenvs.create false; \
  $HOME/.local/bin/poetry install --no-root --no-dev;

RUN echo "Install playwright headless browser..." \
  && playwright install chromium \
  && apt-get install -y libnss3-dev libxss1 libasound2 libxrandr2 \
  libatk1.0-0 libgtk-3-0 libgbm-dev libxshmfence1

COPY bot.py /app/
COPY src /app/src/
