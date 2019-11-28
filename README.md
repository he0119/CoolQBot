# 聊天机器人

[![Build Status](https://dev.azure.com/he0119/CoolQBot/_apis/build/status/he0119.CoolQBot?branchName=master)](https://dev.azure.com/he0119/CoolQBot/_build/latest?definitionId=5&branchName=master)

该机器人利用了
[酷Q](https://cqp.cc/)
、
[CoolQ HTTP API 插件](https://github.com/richardchien/coolq-http-api)
以及
[NoneBot](https://github.com/richardchien/nonebot)
来实现消息接收和发送的功能。

这只是一个随便写写的机器人，主要工作就是按照一定的规则进行复读 ~~（模仿人类）~~，其他功能都是增加可玩性的。

## 运行

## 主要功能

### 复读([repeat](src/plugins/repeat.py))

以一定概率复读群消息

### FFLogs([fflogs](src/plugins/fflogs/__init__.py))

利用 FFLogs 网站提供的 API 获取并计算 DPS 百分比数据
