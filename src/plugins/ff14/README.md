# 最终幻想XIV插件

提供与FF14游戏相关的各种实用功能。

## 功能介绍

- 每日委托配对：记录和查询每日委托任务，查找与自己委托相同的群友
- FFLogs 数据查询：查询副本输出排行榜，支持多种DPS类型查询
- 时尚品鉴 (暖暖)：查询时尚品鉴的搭配攻略
- 物价查询：查询服务器物品价格
- 藏宝选门：帮助选择藏宝图的门

## 使用方法

### 每日委托配对

```bash
/每日委托                            # 查询与自己委托相同的人
/每日委托 乐园都市笑笑镇, 伊弗利特歼灭战, 神龙歼灭战  # 记录每日委托
/每日委托 总览                        # 查看今日所有委托
```

### FFLogs 查询

```bash
/dps update                          # 更新副本数据
/dps 副本名 职业                      # 默认查询 rDPS
/dps 副本名 职业 rdps                 # 查询 rDPS (团队贡献DPS)
/dps 副本名 职业 adps                 # 查询 aDPS (实际DPS)
/dps 副本名 职业 pdps                 # 查询 pDPS (个人DPS)
```

**示例**:

```bash
/dps 绝欧米茄 忍者
/dps 万物终结 黑魔法师 rdps
```

### 时尚品鉴

```bash
/暖暖                                # 查询暖暖攻略
```

### 物价查询

```bash
/物价 物品名                         # 查询物品价格
```

### 藏宝选门

```bash
/gate 2                              # 2个门中选择
/gate 3                              # 3个门中选择
/藏宝选门 2                          # 使用中文别名
/选门 3                              # 使用中文别名
```

## 配置说明

### FFLogs 配置

需要在配置文件中设置 FFLogs 相关参数：

```json
{
  "client_id": "your_fflogs_client_id",
  "client_secret": "your_fflogs_client_secret"
}
```

配置文件位置: `data/config/ff14_fflogs.json`

其他功能无需特殊配置。
