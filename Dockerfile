FROM python:3.8-alpine

WORKDIR /usr/src/app

RUN apk add --no-cache --virtual .build-deps gcc musl-dev

# 安装依赖
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN apk del .build-deps

# 复制 CoolQBot
COPY src/ .

CMD [ "python", "./run.py" ]
