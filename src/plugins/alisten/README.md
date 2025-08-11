# 音乐点播插件

通过外部 Alisten 服务为群组/频道提供跨平台点歌功能。

## 功能介绍

- **多源点播**：支持网易云音乐（wy）、QQ 音乐（qq）和 Bilibili（db）等多个音乐平台。
- **灵活搜索**：可通过歌曲名称、歌手、Bilibili BV 号或指定平台的歌曲名进行精确点播。
- **独立配置**：支持以群组/频道为单位独立配置 Alisten 服务地址、房间号和密码。
- **交互式点播**：当未提供歌曲参数时，会自动进入交互式追问模式，引导用户输入。

## 使用方法

### 基础点播

使用 `/music` 或 `/点歌` 命令，后跟歌曲名称和可选的歌手名。

```bash
/music 稻香                         # 默认使用网易云音乐搜索
/点歌 青花瓷                        # 使用中文别名
/music Sagitta luminis 梶浦由記     # 通过歌曲名 + 歌手名提高准确度
```

### 指定平台搜索

支持通过 `平台:歌曲名` 的格式在特定平台搜索。

```bash
/music BV1Xx411c7md                 # 点播 Bilibili 视频
/music qq:青花瓷                    # 在 QQ 音乐中搜索“青花瓷”
/music wy:稻香                      # 在网易云音乐中搜索“稻香”
```

### 交互式点播

若未提供任何参数，机器人将主动询问。

```bash
/music
# Bot: 你想听哪首歌呢？
```

## 配置说明

本插件需要为每个群组单独配置 Alisten 服务后方可使用。如果当前群组未配置，机器人将返回相应的提示信息。

### 配置命令（仅限超级用户）

```bash
# 设置 Alisten 服务信息
/alisten config set <server_url> <house_id> [house_password]

# 查看当前群组配置
/alisten config show

# 删除当前群组配置
/alisten config delete
```

### 配置示例

```bash
# 基础配置
/alisten config set http://localhost:8080 default

# 带密码的配置
/alisten config set http://localhost:8080 default mypass
```

### 点播规则

插件会根据输入内容自动解析点播来源：

1. `wy:歌曲名` / `qq:歌曲名` / `db:关键词`：在指定平台进行搜索。
2. 以 `BV` 开头：视为 Bilibili 视频，来源设为 `db`。
3. 其他所有情况：视为关键词，使用默认平台（网易云音乐）进行搜索。
