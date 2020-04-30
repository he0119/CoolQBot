# Changelog

一个简单的更新笔记。

## [Unreleased]

## [0.13.1] - 2020-04-30

### Added

- 最终幻想XIV新闻自动推送

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

[Unreleased]: https://github.com/he0119/CoolQBot/compare/v0.13.1...HEAD
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
