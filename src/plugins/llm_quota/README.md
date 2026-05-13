# 大模型额度查询插件

查询大模型剩余额度。

## 限制

仅支持 Tailscale Aperture 格式的 API。

## 配置

在 `.env` 或 `.env.prod` 中配置：

```dotenv
LLM_QUOTA_API_URL=https://your-api-url.com/api/quotas
```

默认值：`https://ai.long-antares.ts.net/api/quotas`

## 命令

- `/quota` 或 `/额度`：查询剩余额度
