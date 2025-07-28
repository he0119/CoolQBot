# 群组绑定插件

群组绑定插件允许将多个群组绑定在一起，实现跨群组的功能同步。

## 功能特性

- 🔗 **群组绑定**：将当前群组绑定到指定的目标群组
- 🔄 **绑定更新**：如果已绑定，可以更新绑定的目标群组
- 🔓 **解除绑定**：将当前群组从绑定关系中移除
- 📋 **查看状态**：查看当前群组的绑定状态
- 👥 **获取绑定群组列表**：获取所有绑定到同一目标的群组ID列表

## 命令使用

### 绑定群组

```bash
/绑定群组 <目标群组ID>
```

将当前群组绑定到指定的目标群组。如果当前群组已经绑定到其他群组，会更新绑定关系。

**示例**：

```bash
/绑定群组 123456789
```

### 解绑群组

```bash
/解绑群组
```

将当前群组从绑定关系中移除。

### 查看绑定状态

```bash
/查看绑定
```

查看当前群组是否已绑定以及绑定的目标群组ID。

## 权限要求

所有命令都需要**超级用户权限**才能执行。

## 使用场景

1. **多群同步**：将多个相关群组绑定在一起，实现功能的统一管理
2. **群组迁移**：当需要更换主群时，可以更新绑定关系
3. **分群管理**：对于有多个分群的大型社区，可以将分群绑定到主群

## 绑定关系说明

### 绑定模式

- 群组绑定采用**多对一**的模式
- 多个群组可以绑定到同一个目标群组
- 一个群组只能绑定到一个目标群组

### 示例场景

假设有群组 A、B、C：

- 群组 B 绑定到群组 A
- 群组 C 绑定到群组 A
- 此时 A 是目标群组，B 和 C 是绑定群组

调用 `get_bound_session_ids("B")` 会返回 `["A", "B", "C"]`

## API 接口

### GroupBindService 类

插件提供了 `GroupBindService` 类，包含以下方法：

#### `bind_group(session_id: str, bind_id: str)`

绑定群组到目标群组，如果已绑定则更新绑定关系。

#### `unbind_group(session_id: str)`

解除群组绑定。

#### `get_bind_id(session_id: str) -> str`

获取群组绑定的目标群组ID，如果未绑定则返回自身ID。

#### `get_bound_session_ids(session_id: str) -> list[str]`

获取所有绑定到同一目标的群组ID列表。

#### `is_group_bound(session_id: str) -> bool`

检查群组是否已绑定。

### 使用示例

```python
from src.plugins.group_bind.data_source import group_bind_service

# 绑定群组
await group_bind_service.bind_group("group_1", "group_main")

# 获取绑定的目标群组
bind_id = await group_bind_service.get_bind_id("group_1")

# 获取所有绑定群组
bound_groups = await group_bind_service.get_bound_session_ids("group_1")

# 检查是否已绑定
is_bound = await group_bind_service.is_group_bound("group_1")

# 解除绑定
await group_bind_service.unbind_group("group_1")
```

## 数据模型

### GroupBind

```python
class GroupBind(Model):
    id: Mapped[int]  # 主键
    session_id: Mapped[str]  # 群组ID
    bind_id: Mapped[str]  # 绑定的目标群组ID
```

## 依赖插件

- `nonebot_plugin_orm`：ORM 支持
- `nonebot_plugin_user`：用户会话管理
- `nonebot_plugin_alconna`：命令解析
- `nonebot_plugin_uninfo`：统一信息接口

## 注意事项

1. 所有命令只能在群组环境中使用
2. 不能将群组绑定到自己
3. 绑定关系是持久化的，会保存到数据库中
4. 解绑时如果群组未绑定会抛出错误
5. 群组绑定更新是原子操作，不会出现中间状态

## 错误处理

- 当尝试解绑未绑定的群组时，会抛出 `ValueError`
- 其他数据库操作错误会向上传播
- 命令处理中的错误会通过机器人消息反馈给用户
