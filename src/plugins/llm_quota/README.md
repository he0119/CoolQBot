# 大模型额度查询插件

查询大模型剩余额度。

## 限制

- 仅支持 Tailscale Aperture 格式的 API
- 仅管理员可使用此插件

## 命令

| 命令                   | 别名    | 说明              | 权限   |
| ---------------------- | ------- | ----------------- | ------ |
| `/quota`               | `/额度` | 查询剩余额度      | 管理员 |
| `/quota set <api_url>` | -       | 设置群组 API 地址 | 管理员 |
| `/quota remove`        | -       | 删除群组 API 配置 | 管理员 |

## 使用说明

1. 管理员使用 `/quota set` 命令设置群组的 API 地址
2. 管理员使用 `/quota` 命令查询剩余额度

## 示例

```
# 设置 API 地址
/quota set https://ai.long-antares.ts.net/api/quotas

# 查询额度
/quota

# 删除配置
/quota remove
```
