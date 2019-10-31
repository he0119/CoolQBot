FROM richardchien/cqhttp:4.12.2

# 安装 Python3.7 和 Vim
RUN add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y python3.7 vim \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists \
    && curl https://bootstrap.pypa.io/get-pip.py | python3.7

# 设置环境变量
ENV CQHTTP_SERVE_DATA_FILES=true \
    CQHTTP_WS_REVERSE_API_URL=ws://127.0.0.1:8080/ws/api/ \
    CQHTTP_WS_REVERSE_EVENT_URL=ws://127.0.0.1:8080/ws/event/ \
    CQHTTP_USE_WS_REVERSE=true \
    CQHTTP_SHOW_LOG_CONSOLE=false

# 安装依赖
COPY requirements.txt /home/user/coolqbot/requirements.txt
RUN pip3.7 install -r /home/user/coolqbot/requirements.txt

# 复制 CoolQBot
COPY src /home/user/coolqbot

# 设置权限
RUN echo "\nmkdir /home/user/coolqbot/bot && chown -R user:user /home/user/coolqbot/bot" >> /etc/cont-init.d/110-get-coolq

# TODO: 通过服务来启动聊天机器人
RUN echo "\nsudo -E -Hu user /usr/bin/python3.7 /home/user/coolqbot/run.py &" >> /etc/cont-init.d/110-get-coolq
