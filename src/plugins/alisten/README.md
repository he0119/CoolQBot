# 音乐插件

通过 alisten 服务提供点歌服务。

## 功能介绍

- 支持网易云音乐、QQ音乐、Bilibili 等多平台音乐源
- 通过自然语言搜索歌曲
- 支持 BV 号直接点播 Bilibili 视频
- 音乐会被添加到 alisten 服务的播放队列中

## 配置

在环境变量或 `.env` 文件中设置以下配置：

```bash
# alisten 服务器地址
ALISTEN_SERVER_URL=http://localhost:8080

# 房间ID（默认为 default）
ALISTEN_HOUSE_ID=default

# 房间密码（如果房间有密码保护）
ALISTEN_HOUSE_PASSWORD=
```

## 使用方法

### 基础点歌

```bash
/music 稻香                          # 使用歌曲名搜索（默认网易云音乐）
/点歌 青花瓷                         # 使用中文别名
```

### 精确搜索

当仅凭歌曲名称无法获得正确结果时，可以添加歌手信息：

```bash
/music Sagitta luminis 梶浦由記      # 歌曲名 + 歌手名
/点歌 夜曲 孙燕姿                    # 中文歌曲 + 歌手名
```

### 指定音乐源

```bash
/music wy:歌曲ID                     # 网易云音乐
/music qq:歌曲ID                     # QQ音乐
/music BV1Xx411c7md                  # Bilibili（直接使用BV号）
```

### 互动式点歌

如果没有提供歌曲名称，机器人会询问你想听什么歌。

## 支持的音乐源

- **wy/netease**: 网易云音乐
- **qq**: QQ音乐
- **db**: Bilibili（支持BV号）

## 注意事项

1. 需要先启动并配置 alisten 服务
2. 确保机器人能够访问 alisten 服务器
3. 歌曲会被添加到队列中，而不是立即播放
4. 点歌成功后会显示歌曲信息和来源平台

```bash
/music                               # 不提供参数时会询问歌曲信息
```

## 配置说明

无需特殊配置，依赖网易云音乐 API 服务。机器人需要在支持音乐卡片的平台上使用（如QQ）。
