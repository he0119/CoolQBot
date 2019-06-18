# Changelog

一个简单的更新笔记。

## [Unreleased]

## [0.8.0] - 2019-06-18

## Added

- 支持自然语言处理
- 支持权限管理

## Changed

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

[Unreleased]: https://github.com/he0119/CoolQBot/compare/v0.8.0...HEAD
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
