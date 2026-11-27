<!-- markdownlint-disable-next-line MD033 MD041 -->
<div align="center">

# CoolQBot

![CI](https://github.com/he0119/CoolQBot/workflows/CI/badge.svg)
[![Codecov](https://codecov.io/gh/he0119/CoolQBot/branch/main/graph/badge.svg?token=QEC2IWAREH)](https://codecov.io/gh/he0119/CoolQBot)
[![Powered by NoneBot](https://img.shields.io/badge/Powered%20%20by-NoneBot-red)](https://github.com/nonebot/nonebot2)
[![Website](https://img.shields.io/badge/Website-CoolQBot-c9ff4a)](https://bot-docs.hehome.xyz/)

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

## 功能

访问 [CoolQBot 功能介绍网站](https://bot-docs.hehome.xyz/) 浏览主要功能与常用命令。

完成部署之后，也可以直接向机器人发送 `/help` 命令获取当前平台和群组可用的功能介绍。

### 绘图

本群启用至少一个生图模型后，即可用 `/draw 画一只猫` 或 `/chat -d 画一只猫`，不需要启用聊天模型。
`/chat -i` 允许聊天模型按需调用生图，单轮最多一次；`/chat -a` 不自动启用生图。

`--image-model` 按配置名选本次生图模型。直接绘图中的旧选项 `--model` 已改义，现为 `--image-model` 别名；
普通聊天（包括 `/chat -i`）的 `--model` 仍只选聊天模型。未指定时，优先使用本群 `/llm model set-image`
设置的兼容模型，再从本群已启用模型按全局声明顺序选。回复会标明实际使用的配置名。

直接绘图也能从描述中识别明确的输出要求，不需要聊天模型：例如 `/draw 画一张 960 像素见方的动态贴纸`
要求 960×960 的多帧 GIF，`/draw 输出 1536×1024 的 WebP 横幅` 要求精确尺寸和格式。
支持宽高、方形像素边长、GIF/PNG/JPEG/WebP、动图，以及「高清 / HD」（固定为 2880×2880）。
也可写 `16:9`、`9:16` 或 `4:3`。只指定比例时，以候选模型默认尺寸的短边为准；默认尺寸为 `auto` 或未设置时，
短边取 1024 像素。对官方 GPT-Image-2.6 Images 直连，推算结果对齐到 16 像素，例如默认短边 1024 时，
`16:9` 请求 `1824x1024`；其他接入保留整数取整。自然语言中同时写「高清」和比例时，以短边 2880 为目标；
官方直连必要时取不超上限的最大输出（如高清 `16:9` 为 `3840x2160`）。明确写出的像素不会改写。
同时写出确切宽高和比例时，两者必须一致。
`--format`、`--size`、`--hd` 优先于同字段的自然语言要求；描述中的明确像素尺寸优先于「高清」。
引号里的文字和「动态光影」等风格描述不作为输出要求，其余描述仍原样传给模型。
要求冲突或没有满足要求的模型时先提示，不发出图片请求；回包不符合则报错，不自动重画。
GIF 要求至少两帧；群端能否播放取决于平台适配器。

管理员可在模型配置中用 `image_output_formats`、`image_sizes` 声明当前接入接受的可变值，
用 `image_sizes_by_format` 覆盖某个格式的尺寸范围；固定的 `extra_body.output_format`、`extra_body.size` 也可作为支持声明。
直连 `https://api.openai.com/v1` 的 Sunburst／Flare 可按[官方像素限制](https://developers.openai.com/api/docs/guides/image-generation#customize-image-output)
使用 PNG/JPEG/WebP，无需枚举每个静态尺寸；管理员设置的格式和尺寸范围仍有效。

官方 GIF 须由管理员确认项目已获得预览权限，并声明可用的格式和帧尺寸。已验证的官方组合示例：

```json
{
  "image_output_formats": ["png", "gif"],
  "image_sizes_by_format": { "gif": ["960x960"] },
  "extra_body": { "frame_count": 2, "frame_duration_ms": 500 }
}
```

用户省略 GIF 尺寸且只声明一个可用尺寸时，用该尺寸；明确请求的 `1024x1024` 不会改成 `960x960`。
GIF 的总图集限制依帧尺寸和帧数而定，同一个模型名经其他网关接入也不代表拥有官方项目权限。
GIF 动画参数不发送到标准 Responses。

直接绘图的 `-c` 仅支持同一生图模型的 Responses 原生记录；Images 接口只生成，不支持参考图和续画。
Responses 图片任务保留已配置图片工具的标准参数，普通聊天请求不直接带 Responses 原生图片工具；
启用 `-i` 时，聊天通过所选生图模型自身的连接请求图片。
