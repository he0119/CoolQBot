FROM he0119/coolqbot-env:v0.2.4

# 安装依赖
COPY requirements.txt /home/user/coolqbot/requirements.txt
RUN pip3.7 install -r /home/user/coolqbot/requirements.txt

# 设置权限
RUN echo "\nmkdir /home/user/coolqbot/bot\nchown -R user:user /home/user/coolqbot/bot" >> /etc/cont-init.d/110-get-coolq

# TODO: 通过服务来启动聊天机器人
RUN echo "\nsudo -E -Hu user /usr/bin/python3.7 /home/user/coolqbot/run.py &" >> /etc/cont-init.d/110-get-coolq

# 复制 CoolQBot
COPY src /home/user/coolqbot
