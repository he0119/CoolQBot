FROM python:3.12.4-slim
COPY --from=ghcr.io/astral-sh/uv:0.5.9 /uv /bin/uv

# 编译参数
ARG VERSION="0.20.1"

WORKDIR /app

ENV SENTRY_RELEASE=${VERSION}
# 设置时区
ENV TZ=Asia/Shanghai
# 设置语言
ENV LANG=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8

# 安装依赖
RUN apt-get update \
  && apt-get -y upgrade \
  && apt-get install -y --no-install-recommends git curl locales fontconfig fonts-noto-color-emoji \
  && localedef -i zh_CN -c -f UTF-8 -A /usr/share/locale/locale.alias zh_CN.UTF-8 \
  && apt-get purge -y --auto-remove \
  && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --compile-bytecode

# 安装浏览器
RUN uv run --no-dev playwright install --with-deps chromium

# 缓存表情包制作插件字体与图片
RUN git clone --depth 1 https://github.com/MeetWq/meme-generator.git \
  && cp -r ./meme-generator/resources/fonts /usr/share/fonts/meme-fonts \
  && rm -rf ./meme-generator \
  && fc-cache -fv
RUN uv run --no-dev meme download --url https://raw.githubusercontent.com/MeetWq/meme-generator/

# Gunicorn 配置
COPY ./docker/gunicorn_conf.py /gunicorn_conf.py
COPY ./docker/start.sh /start.sh
RUN chmod +x /start.sh

# 机器人
ENV APP_MODULE=bot:app
# 如果你有多个QQ，且存在 self_id 指定，多个 worker 会导致无法找到其他 websocket 连接
ENV MAX_WORKERS=1

COPY bot.py .env prestart.sh /app/
COPY src /app/src/

CMD ["uv", "run", "--no-dev", "/start.sh"]
