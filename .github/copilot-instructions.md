# CoolQBot AI 编程助手指南

## 项目概览

CoolQBot 是一个基于 [NoneBot2](https://nonebot.dev/) 的多平台聊天机器人，采用模块化的插件架构。它支持 QQ、Discord、Telegram、DoDo、Kaiheila、OneBot V12、Red 和 Satori 等多个平台。主要功能包括复读、签到、天气查询、游戏信息查询等。

## 核心架构模式

### 插件结构

插件是机器人的核心功能单元，位于 `src/plugins/` 目录下。一个典型的插件遵循以下模式：

- **主入口**: `src/plugins/{plugin_name}/__init__.py` - 定义使用 `on_alconna` 的命令处理器和事件响应器。对于简单的插件，业务逻辑可能直接在此文件中实现。
- **服务逻辑**: `src/plugins/{plugin_name}/data_source.py` 或 `*_api.py` - 对于需要复杂数据处理或与外部 API 交互的插件，业务逻辑被封装在单独的服务类或 API 客户端中，以保持主入口文件的整洁。
- **数据模型**: `src/plugins/{plugin_name}/models.py` - 如果插件需要持久化数据，它会定义 SQLAlchemy ORM 模型。
- **子插件**: `src/plugins/{plugin_name}/plugins/` - 更复杂的功能可以分解为子插件。

### 数据库模式

项目使用 `nonebot-plugin-orm` 来统一处理数据库操作，底层为 SQLAlchemy。

```python
# models.py
from nonebot_plugin_orm import Model
from sqlalchemy.orm import Mapped, mapped_column

class SignInHistory(Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    # ... 其他字段

# 在服务或命令处理函数中使用
from nonebot_plugin_orm import get_session

async with get_session() as session:
    # 使用 session 进行数据库查询和操作
    ...
```

### 权限系统

项目使用一个自定义的权限系统来覆盖 NoneBot2 的默认实现。权限检查基于 `nonebot-plugin-user` 提供的 `User` 对象。

- **定义**: `src/utils/permission.py`
- **用法**: `from src.utils.permission import SUPERUSER`

```python
# 在命令处理器中使用
from src.utils.permission import SUPERUSER

some_cmd = on_alconna(
    # ...,
    permission=SUPERUSER, # 仅允许超级用户执行
)
```

## 开发工作流

### 环境与依赖

项目使用 `uv` 进行包和环境管理。

```bash
# 安装或同步依赖
uv sync
# 运行机器人进行开发
uv run nb run
# 应用数据库迁移
uv run nb orm upgrade
# 运行测试
uv run pytest
```

### 测试

测试框架为 `pytest` 和 `nonebug`。

- **测试文件**: 位于 `tests/plugins/{plugin_name}/`。
- **测试配置**: `tests/conftest.py` 是关键，它定义了测试环境、模拟的机器人、适配器以及用户。
- **测试用户**:
  - **超级用户**: `user_id="10"` (昵称: "nickname")
  - **普通用户**: `user_id="10000"` (昵称: "nickname10000")
- **事件模拟**: 使用 `nonebug` 提供的 `fake_group_message_event_v11` 等工具函数来模拟平台事件。

## 关键开发模式

### 命令定义 (Alconna)

所有命令都使用 `nonebot-plugin-alconna` 来定义，这提供了一种强大而灵活的方式来解析命令参数。

```python
# src/plugins/weather/__init__.py
from nonebot_plugin_alconna import Alconna, Args, on_alconna

weather_cmd = on_alconna(
    Alconna("weather", Args["location?#位置", MultiVar(str, flag="+")]),
    aliases={"天气"},
    use_cmd_start=True,
)
```

### 会话与用户识别

- **用户/群组信息**: 使用 `nonebot-plugin-user` 和 `nonebot-plugin-uninfo` 来获取和管理跨平台的用户和会话信息。
- **群组绑定**: `src/plugins/group_bind` 插件提供了一个关键服务，用于将不同平台的群组会话映射到一个统一的内部 ID (`SessionId`)，这对于需要跨平台共享数据的功能至关重要。

```python
# 获取绑定后的群组 ID
from src.plugins.group_bind import SessionId

async def handle_group_command(session_id: SessionId):
    # 这里的 session_id 是经过 group_bind 插件处理后的统一 ID
    pass
```

### Docker 部署

生产环境推荐使用 Docker 进行部署。

- **配置文件**: `docker-compose.yml`
- **依赖服务**: 音乐插件依赖于外部的 `netease_cloud_music_api` 服务，该服务已包含在 Docker Compose 配置中。
- **启动**: `docker compose up -d`
