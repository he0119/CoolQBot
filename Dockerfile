FROM he0119/coolqbot-env:v0.1.1
# 安装依赖
COPY requirements.txt /home/user/coolqbot/requirements.txt
RUN pip3.6 install -r /home/user/coolqbot/requirements.txt
# 复制CoolQBot并运行
COPY src /home/user/coolqbot
RUN chown user:user /home/user/coolqbot/run.py
#TODO: 通过服务来启动聊天机器人
RUN echo "\n\nsudo -E -Hu user /usr/bin/python3.6 /home/user/coolqbot/run.py &" >> /etc/cont-init.d/110-get-coolq
