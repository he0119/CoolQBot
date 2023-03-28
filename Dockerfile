FROM python:3.10 as requirements-stage

WORKDIR /tmp

COPY ./pyproject.toml ./poetry.lock* /tmp/

RUN curl -sSL https://install.python-poetry.org -o install-poetry.py

RUN python install-poetry.py --yes

ENV PATH="${PATH}:/root/.local/bin"

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM tiangolo/uvicorn-gunicorn:python3.10-slim

# 设置时区
ENV TZ=Asia/Shanghai
ENV SENTRY_RELEASE=version
# 设置语言
ENV LANG=zh_CN.UTF-8

# 安装依赖
COPY --from=requirements-stage /tmp/requirements.txt /app/requirements.txt
RUN apt-get update \
  && apt-get -y upgrade \
  && apt-get install -y --no-install-recommends curl locales fontconfig fonts-noto-cjk fonts-noto-color-emoji \
  && localedef -i zh_CN -c -f UTF-8 -A /usr/share/locale/locale.alias zh_CN.UTF-8 \
  && fc-cache -fv \
  && pip install --no-cache-dir --upgrade -r requirements.txt \
  && apt-get purge -y --auto-remove \
  && rm -rf /var/lib/apt/lists/* \
  && rm /app/requirements.txt

RUN meme download --url https://raw.githubusercontent.com/MeetWq/meme-generator

COPY bot.py pyproject.toml .env prestart.sh /app/
COPY src /app/src/
