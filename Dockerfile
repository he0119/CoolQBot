FROM python:3.15.0-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /bin/uv

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
# 确保 uv.lock 保持不变
ENV UV_LOCKED=1
# 不安装开发依赖
ENV UV_NO_DEV=1
# 从缓存中复制而不是链接，因为缓存是挂载的
ENV UV_LINK_MODE=copy

# 安装依赖
# g++ / cmake / make：Python 3.15 下不少依赖还没有 wheel（pycares 要 cmake 编 c-ares，
#   kiwisolver / contourpy 要 g++ 等），只能从源码编译。
# libxml2-dev / libxslt1-dev：lxml 在没有 cp315 wheel 的版本上需要这两个头文件。
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt-get update \
  && apt-get -y upgrade \
  && apt-get install -y --no-install-recommends gcc g++ cmake make git curl locales fontconfig fonts-noto-color-emoji python3-dev ffmpeg libxml2-dev libxslt1-dev \
  && localedef -i zh_CN -c -f UTF-8 -A /usr/share/locale/locale.alias zh_CN.UTF-8

# Python 依赖
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync

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
# 冒烟脚本，供 CI 验证浏览器渲染链路
COPY scripts /app/scripts/

# 健康检查
HEALTHCHECK --interval=5s --timeout=4s --start-period=180s --retries=5 CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

CMD ["uv", "run", "/start.sh"]
