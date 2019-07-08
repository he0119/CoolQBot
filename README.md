# 聊天机器人

[![Build Status](https://dev.azure.com/he0119/CoolQBot/_apis/build/status/he0119.CoolQBot?branchName=master)](https://dev.azure.com/he0119/CoolQBot/_build/latest?definitionId=5&branchName=master)

该机器人利用了
[酷Q](https://cqp.cc/)
、
[CoolQ HTTP API 插件](https://github.com/richardchien/coolq-http-api)
以及
[NoneBot](https://github.com/richardchien/nonebot)
并基于
[CoolQBot-env](https://github.com/he0119/CoolQBot-env)
来实现消息接收和发送的功能。

这只是一个随便写写的机器人，主要工作就是按照一定的规则进行复读 ~~（模仿人类）~~，其他功能都是增加可玩性的。

## 运行

- 新建一个 `coolq` 和 `bot` 文件夹，

- 将 `bot.ini.example` 文件复制到 `/bot/` 文件夹下并重命名为 `bot.ini` 且填入对应配置。

- 提供了 `Docker Image`，使用以下命令即可运行。

  ```shell
  sudo docker pull he0119/coolqbot:latest && \
  sudo docker run -d --restart always --name coolqbot
    -v $(pwd)/coolq:/home/user/coolq \  # 将宿主目录挂载到容器内用于持久化酷 Q 的程序文件
    -v $(pwd)/bot:/home/user/coolqbot/bot \  # 将宿主目录挂载到容器内用于持久化机器人配置和数据文件
    -p 9000:9000 \  # noVNC 端口，用于从浏览器控制酷 Q
    -e COOLQ_ACCOUNT=2062765419 \ # 要登录的 QQ 账号，可选但建议填
    -e VNC_PASSWD=12345687 \ # noVNC 的密码（官方说不能超过 8 个字符，但实测可以超过）
    he0119/coolqbot:latest
  # docker run -ti --rm --name coolqbot-test \
  #   -e COOLQ_URL=http://dlsec.cqp.me/cqp-tuling \ # 专业版
  ```

- 所有配置数据都在 `/bot/` 下。
