# 聊天机器人
[![Build Status](https://dev.azure.com/he0119/CoolQBot/_apis/build/status/he0119.CoolQBot?branchName=master)](https://dev.azure.com/he0119/CoolQBot/_build/latest?definitionId=5&branchName=master)

该机器人利用了
[酷Q](https://cqp.cc/)
、
[CoolQ HTTP API 插件](https://github.com/richardchien/coolq-http-api)
以及
[CQHttp Python SDK with Asynchronous I/O](https://github.com/richardchien/python-aiocqhttp)
来实现消息接收和发送的功能。

这只是一个随便写写的机器人，主要工作就是按照一定的规则进行复读 ~~(模仿人类)~~，其他功能都是增加可玩性的。

## 运行
1. 新建一个 `coolq` 文件夹，并在 `/coolq/bot/` 文件夹下复制并重命名 `bot.conf.example` 为 `bot.conf` 填入对应配置。

2. 提供了 `Docker Image`，使用以下命令即可运行。
```shell
sudo docker pull he0119/coolqbot:latest && \
sudo docker run -d --restart always --name coolqbot
  -v $(pwd)/coolq:/home/user/coolq \  # 将宿主目录挂载到容器内用于持久化酷 Q 的程序文件
  -p 9000:9000 \  # noVNC 端口，用于从浏览器控制酷 Q
  -e COOLQ_ACCOUNT=2062765419 \ # 要登录的 QQ 账号，可选但建议填
  -e VNC_PASSWD=12345687 \ # noVNC 的密码（官方说不能超过 8 个字符，但实测可以超过）
  he0119/coolqbot:latest
# docker run -ti --rm --name coolqbot-test \
#   -e COOLQ_URL=http://dlsec.cqp.me/cqp-tuling \ #专业版
```
3. 所有配置数据都在 `/coolq/bot/` 下。