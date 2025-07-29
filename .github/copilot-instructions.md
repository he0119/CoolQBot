# CoolQBot AI 编程助手指南

## 项目概览

CoolQBot 是基于 NoneBot2 的多平台聊天机器人，支持 QQ、Discord、Telegram 等 9 个平台。项目采用模块化插件架构，主要功能包括复读、签到、游戏查询等。

## 核心架构模式

### 插件结构

- **主入口**: `src/plugins/{plugin_name}/__init__.py` - 定义命令处理器和路由
- **数据服务**: `src/plugins/{plugin_name}/data_source.py` - 业务逻辑服务类
- **数据模型**: `src/plugins/{plugin_name}/model.py` 或 `models.py` - SQLAlchemy ORM 模型
- **子插件**: `src/plugins/{plugin_name}/plugins/` - 功能细分的子模块

### 权限系统

```python
# 使用项目自定义的权限系统，不是 NoneBot2 内置的
from src.utils.permission import SUPERUSER
# 权限检查基于 nonebot-plugin-user 的 User 对象
```

### 数据库模式

```python
# 统一使用 nonebot-plugin-orm 进行数据库操作
from nonebot_plugin_orm import Model, get_session
from sqlalchemy.orm import Mapped, mapped_column

class YourModel(Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    # 服务类模式进行数据操作
```

## 开发工作流

### 环境管理

```bash
# 使用 uv 作为包管理器
uv sync                    # 安装依赖
uv run nb run             # 运行机器人
uv run nb orm upgrade     # 数据库迁移
```

### 测试模式

- 使用 `nonebug` 框架进行插件测试
- 测试文件位于 `tests/plugins/{plugin_name}/`
- 使用 `fake_group_message_event_v11` 等工具函数模拟事件
- 超级用户测试：`user_id=10` 对应配置中的 `nickname` 超级用户

### 配置约定

- 主配置文件：`.env` - 包含平台适配器和插件配置
- 数据存储：`data/` 目录 - 包含 SQLite 数据库和缓存文件
- 测试配置：`tests/conftest.py` - 定义测试环境的超级用户和适配器

## 关键开发模式

### Session ID 处理

```python
# 群组绑定等功能使用 session_id 标识不同平台的群组
# 格式通常为 "QQClient_群组ID"
current_session_id = event.get_session_id()
```

### 事件处理器模式

```python
# 插件使用 Alconna 或传统 on_command 定义命令
from nonebot_plugin_alconna import on_alconna
from nonebot import on_command

# 统一的消息发送使用 SAA (Send Anything Anywhere)
from nonebot_plugin_send_anything_anywhere import Text
await Text("消息内容").send()
```

### 服务类模式

```python
# 业务逻辑封装在服务类中，便于测试和复用
class YourService:
    async def do_something(self, param: str) -> bool:
        async with get_session() as session:
            # 数据库操作
            pass

your_service = YourService()  # 模块级别单例
```

## 平台适配

- 支持 9 个聊天平台，适配器在 `bot.py` 中注册
- 使用 `nonebot-session-to-uninfo` 统一处理不同平台的用户/群组信息
- 测试主要针对 OneBot V11 (QQ) 平台，其他平台通过适配层兼容

## Docker 部署

- 使用 `docker-compose.yml` 进行容器化部署
- 音乐功能依赖外部 API 服务 `netease_cloud_music_api`
- 生产环境推荐使用 Docker 部署以简化依赖管理
