FROM he0119/coolqbot-env:v0.2.0

# 安装依赖
COPY requirements.txt /home/user/coolqbot/requirements.txt
RUN pip3.7 install -r /home/user/coolqbot/requirements.txt

# 复制 CoolQBot 并运行
COPY src /home/user/coolqbot
RUN chown user:user /home/user/coolqbot/run.py

# TODO: 通过服务来启动聊天机器人
RUN echo "\n\nsudo -E -Hu user /usr/bin/python3.7 /home/user/coolqbot/run.py &" >> /etc/cont-init.d/110-get-coolq
