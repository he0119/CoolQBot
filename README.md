# CoolQBot

![ci](https://github.com/he0119/CoolQBot/workflows/ci/badge.svg)

该机器人利用了
[go-cqhttp](https://github.com/Mrs4s/go-cqhttp)
以及
[NoneBot2](https://github.com/nonebot/nonebot2)
来实现消息接收和发送的功能。

这只是一个随便写写的机器人，主要工作就是按照一定的规则进行复读 ~~（模仿人类）~~，其他功能都是增加可玩性的。

关于名称：最早机器人是基于酷Q，然而现在已经是时代的眼泪。想想还是把这个名字保留下来，留作纪念。

## 运行

请先参考 [文档](https://v2.nonebot.dev/guide/getting-started.html#%E9%85%8D%E7%BD%AE-qq-%E5%8D%8F%E8%AE%AE%E7%AB%AF) 配置好 `go-cqhttp`。

接下来就可以尝试第一次运行机器人。

```shell
# 首先克隆代码到本地
git clone https://github.com/he0119/CoolQBot.git
# 配置机器人通用配置
vim .env.prod
# 安装机器人所需依赖
poetry install
# 运行机器人
nb run
```

第一次运行之后会在当前文件夹下创建 `data` 文件夹并生成各个插件的默认配置。

请按需进行调整之后重新运行机器人便可使用。

### Docker

如果你的计算机上安装有 [Docker](https://www.docker.com/get-started) 并且拥有 [Docker Compose](https://docs.docker.com/compose/install/)。

你不需要执行上面的步骤，请直接将仓库中的 `docker-compose.yml` 文件放置在一个你想存放机器人的文件夹内。

```shell
# 然后配置 go-cqhttp，请参考上面的文档
# 以下是单独运行 go-cqhttp 的命令
sudo docker run -it --rm -v $PWD/cqhttp:/data pcrbot/gocqhttp:latest
```

完成 `go-cqhttp` 配置之后在 `docker-compose.yml` 文件所在目录下运行 `sudo docker-compose up -d`，便可启动机器人。

修改完机器人相关配置之后运行 `sudo docker-compose restart` 重启机器人应用配置。

推荐使用 `Docker` 部署，因为机器人的音乐插件依赖于 [netease_cloud_music_api](https://github.com/Binaryify/NeteaseCloudMusicApi)。

## 功能

请完成部署之后，向机器人发送 `/help` 命令获取各种功能的介绍。
