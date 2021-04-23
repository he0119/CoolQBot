FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

ENV TZ Asia/Shanghai

COPY ./pyproject.toml ./poetry.lock /app/
RUN set -ex; \
    python3 -m pip install poetry; \
    poetry config virtualenvs.create false; \
    poetry install --no-root --no-dev; \
    pip install nonebot2==2.0.0a13.post1;

COPY bot.py /app/
COPY src /app/src/
