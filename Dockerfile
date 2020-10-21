FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

ENV TZ Asia/Shanghai

RUN python3 -m pip install poetry && poetry config virtualenvs.create false

COPY ./pyproject.toml ./poetry.lock* bot.py /app/

COPY src/ /app/src/

RUN poetry install --no-root --no-dev
