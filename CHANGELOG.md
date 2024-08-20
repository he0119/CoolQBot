# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/lang/zh-CN/spec/v2.0.0.html).

## [Unreleased]

## [0.19.2] - 2024-08-20

### Fixed

- 再次修复运行迁移脚本时加载插件报错
- 修复无法正常启用和禁用启动问好的问题
- 修复 Discord 适配器无法代理的问题

## [0.19.1] - 2024-08-17

### Added

- 优化 NoneBot 的性能

## [0.19.0] - 2024-08-16

### Added

- 使用 alc 改造插件
- memes 增加表情调用次数统计

### Fixed

- 修复插件订阅 B 站和最终幻想XIV 出错的问题
- 修复运行迁移脚本时加载插件报错
- 修复未配置 QQ 机器人时的报错
- 修复表情包插件字体缺失的问题

## [0.18.1] - 2024-08-07

### Added

- 支持 QQ 机器人平台的校验文件
- 通过脚本更新 fflogs 的数据

## [0.18.0] - 2024-07-22

### Added

- 升级至 Pydantic V2
- 添加 Discord 和 Telegram 适配器
- 新增机器人健康检查 API

### Changed

- 优化每日委托的体验
- 替换内置的超级用户权限
- 直接使用 Python 官方镜像

## [0.17.5] - 2024-02-27

### Added

- 添加每日委托配对查询功能

## [0.17.4] - 2023-11-30

### Added

- 添加 DoDo 和 Villa 适配器

### Fixed

- 修复无法捕获 NoneBot 错误日志的问题
- 修复打卡历史选项不直观的问题

## [0.17.3] - 2023-11-24

### Added

- 支持 QQ 适配器下频道的 admin 权限

### Fixed

- 修复超级管理员权限判断问题
- 通过环境变量设置 token
- 处理参数有多余的空格的情况

## [0.17.2] - 2023-11-22

### Fixed

- 状态插件默认不发送 Disk 数据

## [0.17.1] - 2023-11-21

### Fixed

- 修复获取用户时的报错

## [0.17.0] - 2023-11-20

### Added

- 添加 QQ 适配器
- 添加 Satori 适配器
- 通过用户名判断是否是超级用户

### Changed

- 使用 orm 插件

### Removed

- 移除 gscode 与 pcr 插件

## [0.16.1] - 2023-11-15

### Added

- 添加多适配器支持
- 添加用户插件

### Fixed

- 修复和风天气无法找到城市时报错的问题

## [0.16.0] - 2023-07-28

### Added

- 添加数据库插件
- 添加词云插件
- FFLogs 添加设置缓存的命令
- 适配插件元信息
- 使用 nonebot-plugin-treehelp 生成插件帮助
- 添加赛博医院，支持入院，出院和查房
- 添加打卡功能，支持健身，饮食，体重，体质打卡

### Changed

- 适配 NoneBot2 2.0.0
- 利用新版 NoneBot2 特性简化帮助
- 将 FFlogs 缓存数据存放至缓存目录
- 直接使用 nonebot-bison 0.8.0 版本
- 利用 eorzeaenv 计算艾欧泽亚天气

### Removed

- 删除 `公主连结Re:Dive` 插件中定时推送功能
- 移除机器人插件

## [0.15.3] - 2021-12-19

### Added

- 添加 `最终幻想XIV` 查价功能

## [0.15.2] - 2021-11-21

### Added

- 添加 `最终幻想XIV` 时尚品鉴功能

### Changed

- 升级 nonebot-hk-reporter(nonebot-bison) 至 0.4.0
- 删除订阅插件回复中不需要的换行符

### Removed

- 移除原神插件

## [0.15.1] - 2021-09-17

### Added

- 添加原神 UID 查询

### Changed

- 升级 nonebot-hk-reporter 至 0.3.2
- 将每日早安与启动问候分离开来，可以分别在不同的群启用

## [0.15.0] - 2021-08-29

### Added

- 给数据插件管理添加管理网络文件的方法
- 添加订阅插件([nonebot_hk_reporter](https://github.com/felinae98/nonebot-hk-reporter))

### Changed

- 调整复读规则，不再复读带网址的内容
- 调整插件数据管理的配置访问方式
- 每日早安插件使用自己实现的节假日问候语

### Removed

- 移除 `最终幻想XIV` 与公主链接插件中的新闻订阅功能（可通过订阅插件替代）

### Fixed

- 修复音乐插件内容格式问题
- 修复机器人插件，切换至腾讯自然语言处理

## [0.14.1] - 2021-04-28

### Added

- fflogs 的 boss 数据可以从本地或者仓库获取

### Changed

- 更新至 NoneBot2 2.0.0a13
- `最终幻想XIV` 使用新闻发布日期作为推送判定标准

## [0.14.0] - 2020-11-30

### Added

- 帮助插件
- 支持私聊禁言特定的群
- 给各种功能加上单独的开关
- 可查询他人绑定的角色数据

### Changed

- 升级至 `NoneBot2`
- 更新至最新的和风天气 API

### Removed

- B 站番剧查询
- `yobot` 集成
- `NLP` 相关模块

### Fixed

- 修复数据记录数据没有正常清除的问题
- 修复 fflogs 排行 adps 和 pdps 获取报错

## [0.13.1] - 2020-04-30

### Added

- `最终幻想XIV` 新闻自动推送

### Changed

- 更新和重启 `yobot` 需要管理员权限

## [0.13.0] - 2020-04-24

### Added

- 整合 `yobot`

### Changed

- 修改 `PluginData` 的方法命名

## [0.12.2] - 2020-02-15

### Fixed

- 修复早安插件
- 使用自建的网易云音乐 API

## [0.12.1] - 2020-02-13

### Fixed

- 更新 `nonebot` 至 `1.4.1` 以修复 `render_expression` 的错误
- 修复藏宝选门插件未正确处理不符合参数的问题

### Changed

- 用 `httpx` 替换 `requests`

## [0.12.0] - 2020-02-13

### Added

- 增加了监控 `最终幻想XIV` 服务器状态的功能

### Changed

- 增加艾欧泽亚天气预报的数量

## [0.11.4] - 2020-01-23

### Added

- 添加通过 @他人来获取他人输出数据的功能

## [0.11.3] - 2019-12-27

### Fixed

- 修复 `FFLogs` 插件 在普通或零式只有一个有数据时导致查询无法正确返回数据的错误

## [0.11.2] - 2019-12-14

### Fixed

- 修复群主使用禁言插件时没法正常回复的问题

## [0.11.1] - 2019-12-11

### Added

- `fflogs` 插件现在支持获取指定角色的排名数据

### Changed

- `fflogs` 插件修改和查看 `Token` 需要超级用户权限

## [0.11.0] - 2019-11-29

### Changed

- 将机器人从 CoolQ Docker 镜像中独立出来
- 更新了文档，添加了部署方法和一些插件的使用说明
- 使用 Python 3.8

## [0.10.1] - 2019-11-28

### Fixed

- 修复 `fflogs` 插件中如果副本不存在数据时的报错

## [0.10.0] - 2019-11-27

### Added

- 添加了查询 fflogs 输出百分比的功能

### Fixed

- 修复了复读时卡住导致接下来的复读失败的问题

## [0.9.1] - 2019-09-26

### Changed

- 禁言插件会自动识别权限，并根据拥有的权限做出反应

### Fixed

- 修复了历史插件无法使用的问题

## [0.9.0] - 2019-07-29

### Added

- 支持多个群的复读，排行榜和历史记录
- 可以自动升级旧版本 `recorder` 插件保存的数据
- 青云客智能聊天机器人
- 音乐插件（当前仅支持网易云音乐）
- 天气插件支持查询 `最终幻想XIV` 中的天气

### Changed

- 启动时会根据当前时间发送不同消息
- 统一配置文件位置

### Fixed

- 修复了管理员配置出错的问题

## [0.8.1] - 2019-06-18

### Fixed

- 不复读图片的问题

## [0.8.0] - 2019-06-18

### Added

- 支持自然语言处理
- 支持权限管理

### Changed

- 使用 `NoneBot` 机器人框架

## [0.7.1] - 2019-05-15

### Fixed

- 使用本地时间替换之前的 `UTC` 时间

## [0.7.0] - 2019-05-14

### Added

- 保存每天的复读和发送消息数量
- `history` 插件支持按天查询数据

### Changed

- 升级 `CoolQBot-env` 到 `v0.2.3`
- 删除了天气插件中的百度 API

### Fixed

- 每次保存 `Recorder` 数据时，先清理 `msg_send_time` 列表

## [0.6.2] - 2019-04-14

### Changed

- 移除了检测状态并重启 `酷Q` 的功能
- 升级 `CoolQBot-env` 到 `v0.2.1`
- 改进了 `rank` 插件的正则表达式，现在可以使用 `/rank n100`
- 改进了所有插件的正则表达式，现在命令与参数之间必须要有空格
- `ban` 插件的参数调整为禁言分钟数

## [0.6.1] - 2019-03-28

### Changed

- 使用 `ini` 作为配置文件后缀

### Fixed

- 修复了 `history` 插件查询历史时的错误

## [0.6.0] - 2019-03-27

### Added

- 添加了更新笔记。
- 为 `morning` 插件添加了配置。

### Changed

- 为每个计划任务添加了 `ID`。
- 升级 `CoolQBot-env` 到 `v0.2.0`
- 复读次数排行榜也加入了消息数量过滤

## [0.5.2] - 2019-03-22

### Added

- 添加了读取和设置插件配置数据。
- 添加了 `morning` 插件。

### Changed

- 给 `repeat` 插件添加了配置。

### Fixed

- 修复了 @机器人时，意外复读的问题。

## [0.5.1] - 2019-03-21

### Added

- 添加启动问好。
- 在状态插件中添加在线时间。

## [0.5.0] - 2019-03-19

### Added

- 新增了一个 `PluginData` 类，用来管理插件配置和数据。
- 新增了自主禁言插件。
- 将检查酷 Q 插件状态的函数添加了回来。

### Changed

- 利用 `PluginData` 类重构了代码。

### Fixed

- 修复了 `weather` 和 `bilibili` 插件最后会多一行的问题。

## [0.4.4] - 2019-01-22

### Removed

- 删除了检查酷 Q 状态的函数。

## [0.4.3] - 2018-11-25

### Added

- 增加了 `Vim`，方便修改，测试。

### Changed

- 使用了更好的删除复读记录的方法。

### Fixed

- 修复了服务器时区问题。

## [0.4.2] - 2018-10-14

### Fixed

- 修复了缺少 `dateutil` 依赖导致 `history` 插件无法运行的问题。

## [0.4.1] - 2018-10-14

### Added

- 增加了查询任意月份的排行榜功能。

### Fixed

- 修复了 Linux 下的路径问题。
- 修复了聊天数量统计有误的问题。

## [0.4.0] - 2018-10-13

### Added

- 增加了每月底自动清除复读记录的功能。
- 增加了查看上月复读排行榜的功能 (`/history`)。

## [0.3.0] - 2018-09-30

### Added

- 增加了指路功能（FF14 宝物库）(`/gate`)。

## [0.2.0] - 2018-08-24

### Added

- 增加了复读排行榜插件 (`/rank`)。

### Changed

- 使用 `aiocqhttp` 自带的 `logger`。
- 利用 `config.py` 文件来管理不同平台配置。

## [0.1.2] - 2018-08-15

### Added

- 增加了 NGA 风格的 ROLL 点插件 (`/roll`)。

## [0.1.1] - 2018-08-15

### Added

- 增加了复读群签到。

### Changed

- 部分功能插件支持私聊。

## [0.1.0] - 2018-08-14

### Added

- 正常工作的版本。

[unreleased]: https://github.com/he0119/CoolQBot/compare/v0.19.2...HEAD
[0.19.2]: https://github.com/he0119/CoolQBot/compare/v0.19.1...v0.19.2
[0.19.1]: https://github.com/he0119/CoolQBot/compare/v0.19.0...v0.19.1
[0.19.0]: https://github.com/he0119/CoolQBot/compare/v0.18.1...v0.19.0
[0.18.1]: https://github.com/he0119/CoolQBot/compare/v0.18.0...v0.18.1
[0.18.0]: https://github.com/he0119/CoolQBot/compare/v0.17.5...v0.18.0
[0.17.5]: https://github.com/he0119/CoolQBot/compare/v0.17.4...v0.17.5
[0.17.4]: https://github.com/he0119/CoolQBot/compare/v0.17.3...v0.17.4
[0.17.3]: https://github.com/he0119/CoolQBot/compare/v0.17.2...v0.17.3
[0.17.2]: https://github.com/he0119/CoolQBot/compare/v0.17.1...v0.17.2
[0.17.1]: https://github.com/he0119/CoolQBot/compare/v0.17.0...v0.17.1
[0.17.0]: https://github.com/he0119/CoolQBot/compare/v0.16.1...v0.17.0
[0.16.1]: https://github.com/he0119/CoolQBot/compare/v0.16.0...v0.16.1
[0.16.0]: https://github.com/he0119/CoolQBot/compare/v0.15.3...v0.16.0
[0.15.3]: https://github.com/he0119/CoolQBot/compare/v0.15.2...v0.15.3
[0.15.2]: https://github.com/he0119/CoolQBot/compare/v0.15.1...v0.15.2
[0.15.1]: https://github.com/he0119/CoolQBot/compare/v0.15.0...v0.15.1
[0.15.0]: https://github.com/he0119/CoolQBot/compare/v0.14.1...v0.15.0
[0.14.1]: https://github.com/he0119/CoolQBot/compare/v0.14.0...v0.14.1
[0.14.0]: https://github.com/he0119/CoolQBot/compare/v0.13.1...v0.14.0
[0.13.1]: https://github.com/he0119/CoolQBot/compare/v0.13.0...v0.13.1
[0.13.0]: https://github.com/he0119/CoolQBot/compare/v0.12.2...v0.13.0
[0.12.2]: https://github.com/he0119/CoolQBot/compare/v0.12.1...v0.12.2
[0.12.1]: https://github.com/he0119/CoolQBot/compare/v0.12.0...v0.12.1
[0.12.0]: https://github.com/he0119/CoolQBot/compare/v0.11.4...v0.12.0
[0.11.4]: https://github.com/he0119/CoolQBot/compare/v0.11.3...v0.11.4
[0.11.3]: https://github.com/he0119/CoolQBot/compare/v0.11.2...v0.11.3
[0.11.2]: https://github.com/he0119/CoolQBot/compare/v0.11.1...v0.11.2
[0.11.1]: https://github.com/he0119/CoolQBot/compare/v0.11.0...v0.11.1
[0.11.0]: https://github.com/he0119/CoolQBot/compare/v0.10.1...v0.11.0
[0.10.1]: https://github.com/he0119/CoolQBot/compare/v0.10.0...v0.10.1
[0.10.0]: https://github.com/he0119/CoolQBot/compare/v0.9.1...v0.10.0
[0.9.1]: https://github.com/he0119/CoolQBot/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/he0119/CoolQBot/compare/v0.8.1...v0.9.0
[0.8.1]: https://github.com/he0119/CoolQBot/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/he0119/CoolQBot/compare/v0.7.1...v0.8.0
[0.7.1]: https://github.com/he0119/CoolQBot/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/he0119/CoolQBot/compare/v0.6.2...v0.7.0
[0.6.2]: https://github.com/he0119/CoolQBot/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/he0119/CoolQBot/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/he0119/CoolQBot/compare/v0.5.2...v0.6.0
[0.5.2]: https://github.com/he0119/CoolQBot/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/he0119/CoolQBot/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/he0119/CoolQBot/compare/v0.4.4...v0.5.0
[0.4.4]: https://github.com/he0119/CoolQBot/compare/v0.4.3...v0.4.4
[0.4.3]: https://github.com/he0119/CoolQBot/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/he0119/CoolQBot/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/he0119/CoolQBot/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/he0119/CoolQBot/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/he0119/CoolQBot/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/he0119/CoolQBot/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/he0119/CoolQBot/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/he0119/CoolQBot/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/he0119/CoolQBot/releases/tag/v0.1.0
