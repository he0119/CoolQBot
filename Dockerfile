FROM python:3.12.4-slim

WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
ENV SENTRY_RELEASE=version
# 设置语言
ENV LANG=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8

# Gunicon 配置
COPY ./docker/start.sh /start.sh
RUN chmod +x /start.sh

COPY ./docker/gunicorn_conf.py /gunicorn_conf.py

# 安装依赖
RUN apt-get update \
  && apt-get -y upgrade \
  && apt-get install -y --no-install-recommends curl locales fontconfig fonts-noto-cjk fonts-noto-color-emoji \
  && localedef -i zh_CN -c -f UTF-8 -A /usr/share/locale/locale.alias zh_CN.UTF-8 \
  && fc-cache -fv \
  && apt-get purge -y --auto-remove \
  && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.lock ./
RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -r requirements.lock

# 提前缓存插件所需数据
RUN playwright install --with-deps chromium
RUN meme download --url https://raw.githubusercontent.com/MeetWq/meme-generator/

# Bot
ENV APP_MODULE=bot:app
# # 如果你有多个QQ，且存在 self_id 指定，多个 worker 会导致无法找到其他 websocket 连接
ENV MAX_WORKERS=1

COPY bot.py pyproject.toml .env prestart.sh /app/
COPY src /app/src/

CMD ["/start.sh"]
