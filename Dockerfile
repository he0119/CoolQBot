FROM python:3.13.1-slim
COPY --from=ghcr.io/astral-sh/uv:0.5.13 /uv /bin/uv

# 编译参数
ARG VERSION

# 设置工作目录
WORKDIR /app

# 设置 Sentry Release 版本
ENV SENTRY_RELEASE=${VERSION}
# 设置时区
ENV TZ=Asia/Shanghai
# 设置语言
ENV LANG=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8

# 启用字节码编译，加速机器人启动
ENV UV_COMPILE_BYTECODE=1
# 在不更新 uv.lock 文件的情况下运行
ENV UV_FROZEN=1
# 从缓存中复制而不是链接，因为缓存是挂载的
ENV UV_LINK_MODE=copy

# 安装依赖
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt-get update \
  && apt-get -y upgrade \
  && apt-get install -y --no-install-recommends gcc git curl locales fontconfig fonts-noto-color-emoji \
  && localedef -i zh_CN -c -f UTF-8 -A /usr/share/locale/locale.alias zh_CN.UTF-8

# Python 依赖
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --no-dev

# 安装浏览器
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  uv run --no-dev playwright install --with-deps chromium

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

# 机器人本体
COPY bot.py .env prestart.sh /app/
COPY src /app/src/

# 健康检查
HEALTHCHECK --interval=5s --timeout=4s --start-period=180s --retries=5 CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

CMD ["uv", "run", "--no-dev", "/start.sh"]
