# Changelog
简单的更新笔记

## [Unreleased]
### Added
- 添加了更新笔记

### Changed
- 为每个计划任务添加了`ID`

## [0.5.2] - 2019-03-22
### Added
- 添加了读取和设置插件配置数据
- 添加了`morning`插件

### Changed
- 给`repeat`插件添加了配置

### Fixed
- 修复了@机器人时，意外复读的问题


## [0.5.1] - 2019-03-21
### Added
- 添加启动问好
- 在状态插件中添加在线时间

## [0.5.0] - 2019-03-19
### Added
- 新增了一个`PluginData`类，用来管理插件配置和数据
- 新增了自主禁言插件
- 将检查酷Q插件状态的函数添加了回来

### Changed
- 利用`PluginData`类重构了代码

### Fixed
- 修复了天气和`bilibili`插件最后会多一行的问题

## [0.4.4] - 2019-01-22
### Removed
- 删除了检查酷Q状态的函数

## [0.4.3] - 2018-11-25
### Added
- 增加了Vim，方便修改，测试

### Changed
- 使用了更好的删除复读记录的方法

### Fixed
- 修复了服务器时区问题

## [0.4.2] - 2018-10-14
### Fixed
- 修复了缺少`dateutil`依赖导致`history`插件无法运行的问题

## [0.4.1] - 2018-10-14
### Added
- 增加了查询任意月份的排行榜功能

### Fixed
- 修复了Linux下的路径问题
- 修复了聊天数量统计有误的问题

## [0.4.0] - 2018-10-13
### Added
- 增加了每月底自动清除复读记录的功能
- 增加了查看上月复读排行榜的功能

## [0.3.0] - 2018-09-30
### Added
- 增加了指路功能（FF14宝物库）

## [0.2.0] - 2018-08-24
### Added
- 增加了复读排行榜插件

### Changed
- 使用`aiocqhttp`自带的`logger`
- 利用`config.py`文件来管理不同平台配置

## [0.1.2] - 2018-08-15
### Added
- 增加了NGA风格的ROLL点插件

## [0.1.1] - 2018-08-15
### Added
- 增加了复读群签到

### Changed
- 部分功能插件支持私聊。

## [0.1.0] - 2018-08-14
### Added
- 正常工作的版本





[Unreleased]: https://github.com/he0119/CoolQBot/compare/v0.5.2...HEAD
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