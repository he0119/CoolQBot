<!-- markdownlint-disable-next-line MD033 MD041 -->
<div align="center">

# CoolQBot

![CI](https://github.com/he0119/CoolQBot/workflows/CI/badge.svg)
[![codecov](https://codecov.io/gh/he0119/CoolQBot/branch/master/graph/badge.svg?token=QEC2IWAREH)](https://codecov.io/gh/he0119/CoolQBot)
[![Powered by NoneBot](https://img.shields.io/badge/Powered%20%20by-NoneBot-red)](https://github.com/nonebot/nonebot2)

</div>

这只是一个随便写写的机器人，主要工作就是按照一定的规则进行复读 ~~（模仿人类）~~，其他功能都是增加可玩性的。

关于名称：最早机器人是基于 `酷Q`，然而现在已经是时代的眼泪。想想还是把这个名字保留下来，留作纪念。

## 运行

<!-- markdownlint-disable-next-line MD013 -->

```shell
# 首先克隆代码到本地
git clone https://github.com/he0119/CoolQBot.git
# 安装机器人所需依赖
uv sync
# 配置机器人通用配置
vim .env
```

请先参考 [.env](./.env) 配置项注释中的链接，配置好所需的适配器，同时填写好各种插件的配置。

接下来就可以尝试运行机器人。

```shell
# 初始化数据库
uv run nb orm upgrade
# 运行机器人
uv run nb run
```

### Docker

如果你的计算机上安装有 [Docker](https://www.docker.com/get-started)。

你不需要执行上面的步骤，请直接将仓库中的 `docker-compose.yml` 和 `.env` 文件放置在一个你想存放机器人的文件夹内。

请先参考 [.env](./.env) 配置项注释中的链接，配置好所需的适配器，同时填写好各种插件的配置。

完成配置之后在 `docker-compose.yml` 文件所在目录下运行 `sudo docker compose up -d`，便可启动机器人。

推荐使用 `Docker` 部署，因为机器人的音乐插件依赖于 [netease_cloud_music_api](https://github.com/Binaryify/NeteaseCloudMusicApi)。

## 功能

请完成部署之后，向机器人发送 `/help` 命令获取各种功能的介绍。
