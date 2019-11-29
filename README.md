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

机器人的运行离不开 [酷Q](https://cqp.cc/) 与 [CoolQ HTTP API 插件](https://cqhttp.cc/docs/)，请参考其文档完成插件安装并成功运行。

此机器人基于 [NoneBot](https://github.com/richardchien/nonebot) ，请参考其 [文档](https://nonebot.cqp.moe/guide/getting-started.html) 完成 `CoolQ HTTP API 插件` 的配置。

接下来就可以尝试第一次运行机器人。

```shell
# 首先克隆代码到本地
$git clone https://github.com/he0119/CoolQBot.git
# 安装机器人所需依赖
$pip install requirements.txt
# 运行机器人
cd ./src && python ./run.py
```

第一次运行之后会在 `src` 文件夹下创建 `bot` 文件夹并生成机器人和各个插件的默认配置。

请按需进行调整之后重新运行机器人便可使用。

### Docker

如果你的计算机上安装有 `Docker` 并且拥有 `Docker Compose`。

请直接将仓库中的 `docker-compose.yml` 文件放置在一个你想存放机器人的文件夹内。

按需调整 `docker-compose.yml` 文件中的 `VNC_PASSWD` `COOLQ_ACCOUNT` 的值之后。

运行 `sudo docker-compose up -d`，便可同时启动机器人，[酷Q](https://cqp.cc/) 和 [CoolQ HTTP API 插件](https://github.com/richardchien/coolq-http-api)。

然后访问 `http://<你的IP>:9000/` 进入 `noVNC`（密码为 `VNC_PASSWD` 的值），登录 `酷Q`，即可开始使用。

修改完配置之后运行 `sudo docker-compose restart` 重启机器人应用配置。

## 主要功能

所有功能都是以插件的形式实现。

### 复读([repeat](src/plugins/repeat.py))

以一定概率复读群消息。

#### 用法

在群里发送消息，会触发复读。

#### 设置

- `repeat_rate`：复读的概率（百分比）
- `repeat_interval`：复读间隔，每次复读之后下次复读必须等待的时间（分钟）

#### 示例

```plaintext
群友A：\小誓约最可爱/
小誓约：\小誓约最可爱/
群友B：\小誓约最可爱/
群友C：\小誓约最可爱/
```

### 机器人([robot](src/plugins/robot/__init__.py))

提供基于文本的基础聊天能力。

支持 [图灵机器人](http://www.turingapi.com/) 和 [腾讯机器人](https://ai.qq.com/)。

#### 用法

使用 `称呼` 或者 `@机器人` 即可触发聊天的功能。

#### 设置

- `tuling-api_key`：图灵机器人的 `API_KEY`
- `tencent-app_id`：腾讯 AI 的 `app_id`
- `tencent-app_key`：腾讯 AI 的 `app_key`

请至少配置 `图灵机器人` 或者 `腾讯 AI` 其中之一，否则该功能无法运行。

#### 示例

```plaintext
群友A：小誓约最可爱！
小誓约：@群友A 你最可爱你最萌
群友B：@小誓约 你最可爱！
小誓约：@群友B 你最可爱你最萌
```

### FFLogs([fflogs](src/plugins/fflogs/__init__.py))

利用 FFLogs 网站提供的 API 获取并计算 DPS 百分比数据。

#### 用法

/dps 副本名 职业 [DPS 种类】

DPS 种类如果不填写默认为 `rdps`，且支持 `adps` 和 `pdps`。

#### 设置

- `fflogs-token`：FFLogs 网站的 API_KEY
- `fflogs-range`：计算百分比的范围（天）
- `cache-hour`：定时缓存数据的时间 - 时
- `cache-minute`：定时缓存数据的时间 - 分
- `cache-second`：定时缓存数据的时间 - 秒

#### 示例

```plaintext
群友A：/dps 10王 白魔
小誓约：提坦妮雅歼殛战 白魔法师 的数据(rdps)
        数据总数：1507 条
        100% : 7865.16
        99% : 7271.02
        95% : 6783.36
        75% : 5958.52
        50% : 5248.24
        25% : 4424.57
        10% : 3683.76
```
