# 大模型对话插件

接入多种大模型 API，提供智能对话与问答功能。

## 支持的 API 格式

| 格式        | 请求地址                      | 认证方式                | 适用服务                              |
| ----------- | ----------------------------- | ----------------------- | ------------------------------------- |
| `chat`      | `{base_url}/chat/completions` | `Authorization: Bearer` | DeepSeek、OpenAI 兼容接口、硅基流动等 |
| `responses` | `{base_url}/responses`        | `Authorization: Bearer` | OpenAI Responses API                  |
| `anthropic` | `{base_url}/v1/messages`      | `x-api-key`             | Anthropic Claude                      |

三种格式在请求结构上差异较大（system 提示词的位置、工具定义的嵌套层级、图片编码方式、
用量字段名各不相同），插件内部统一归一化，命令与配置的使用方式完全一致。

## 功能

- 单轮与多轮对话，多轮支持「结束」「回滚」指令
- 流式与非流式请求
- 推理内容展示（DeepSeek 的 `reasoning_content`、Anthropic 的 `thinking`、Responses 的推理摘要）
- 工具调用（function calling），三种格式自动适配
- 图片输入（多模态）
- 在回复末尾显示整轮耗时、实际模型和 token 用量，工具调用产生的多次请求会累计统计
- Markdown 转图片
- TTS 语音回复（GPT-SoVITS）
- 按模型查询剩余额度，支持 Tailscale Aperture 与 DeepSeek 官方余额接口

## 请求标识

大模型请求会发送以下标识头：

- `User-Agent: CoolQBot/<当前版本>`：版本读取自 `pyproject.toml` 的 `[project].version`。
- `X-Session-Affinity: <随机会话 ID>`：每次创建 LLM 对话上下文时生成；同一轮工具调用和多轮对话保持一致，新的 `/llm` 调用会重新生成。不会发送群号或用户 ID。

## 命令

| 命令                           | 别名              | 说明                  | 权限   |
| ------------------------------ | ----------------- | --------------------- | ------ |
| `/llm <内容>`                  | `/ai`             | 与模型对话            | 所有人 |
| `/llm <内容> --model <模型名>` | -                 | 本次使用指定模型      | 所有人 |
| `/llm <内容> -c`               | -                 | 启用多轮对话          | 所有人 |
| `/llm <内容> -r`               | -                 | 把回复渲染成图片      | 所有人 |
| `/llm <内容> -t`               | -                 | 使用语音回复          | 所有人 |
| `/llm model --list`            | -                 | 查看可用模型列表      | 所有人 |
| `/llm model --set <模型名>`    | -                 | 设置群组默认模型      | 所有人 |
| `/llm tts --list`              | -                 | 查看可用 TTS 模型列表 | 所有人 |
| `/llm tts --set <模型名>`      | -                 | 设置群组默认 TTS 模型 | 所有人 |
| `/llm quota [模型名]`          | `/quota`、`/额度` | 查询模型剩余额度      | 所有人 |

## 使用方法

### 基础对话

```bash
/llm 帮我写一段冒泡排序          # 与默认模型对话
/ai 今天心情不好                 # 使用别名
/llm 这张图是什么                # 附带图片时会一起发给模型
```

### 指定模型

```bash
/llm model --list                # 查看有哪些模型
/llm 讲个笑话 --model claude     # 本次使用 claude
/llm model --set claude          # 之后本群默认使用 claude
/llm quota                       # 查询本群当前模型的剩余额度
/llm quota deepseek              # 查询指定模型的剩余额度
/quota deepseek                  # 使用快捷命令查询指定模型的剩余额度
```

### 多轮对话

```bash
/llm -c 我们来玩成语接龙
# 之后直接发消息继续对话
# 发送「结束」结束对话，「回滚」撤销上一轮
```

### 图片与语音

```bash
/llm -r 用表格对比 Python 和 Go  # 回复渲染成图片
/llm tts --set 派蒙              # 设置语音模型
/llm -t 念一首诗                 # 用语音回复
```

## 配置说明

通过 `LLM__` 前缀在 `.env` 中配置。`models` 的第一项为默认模型。

```env
# 全局服务地址，未单独配置服务地址的模型都用它；留空则按 API 格式取内置默认值
LLM__BASE_URL=https://api.example.com
# 全局密钥，未单独配置密钥的模型都用它
LLM__API_KEY=sk-xxx
# 全局人设
LLM__PROMPT=你是一个乐于助人的助手
# 是否展示推理内容
LLM__SEND_THINKING=true
# 是否默认把回复渲染成图片
LLM__MD_TO_PIC=false
# 是否流式请求
LLM__STREAM=false
# 单次提问允许的最大工具调用轮数
LLM__MAX_TOOL_ROUNDS=5
# 多轮对话等待用户输入的超时时间（秒）
LLM__CONTEXT_TIMEOUT=120

# 模型列表
LLM__MODELS='
[
  {
    "name": "deepseek",
    "provider": "chat",
    "model": "deepseek-chat",
    "quota": {
      "provider": "deepseek"
    }
  },
  {
    "name": "deepseek-aperture",
    "provider": "chat",
    "model": "deepseek-chat",
    "base_url": "https://ai.example.com/v1",
    "quota": {
      "provider": "aperture",
      "bucket": "deepseek"
    }
  },
  {
    "name": "gpt",
    "provider": "responses",
    "model": "gpt-5",
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-openai-xxx"
  },
  {
    "name": "claude",
    "provider": "anthropic",
    "model": "claude-opus-5",
    "base_url": "https://api.anthropic.com",
    "api_key": "sk-ant-xxx",
    "max_tokens": 8192
  }
]
'

# TTS（可选，留空则禁用语音功能）
LLM__TTS_BASE_URL=http://127.0.0.1:9880
LLM__TTS_ACCESS_TOKEN=your_token
LLM__TTS_MODEL=default
```

### 单个模型的可配置项

| 字段          | 说明                                                    |
| ------------- | ------------------------------------------------------- |
| `name`        | 模型标识，命令中用此名称选择模型                        |
| `model`       | 传给 API 的模型名，留空时与 `name` 相同                 |
| `provider`    | API 格式，`chat` / `responses` / `anthropic`            |
| `base_url`    | 服务地址，留空时回退到 `LLM__BASE_URL` 或按格式取默认值 |
| `api_key`     | 密钥，留空时回退到 `LLM__API_KEY`                       |
| `prompt`      | 人设，留空时回退到 `LLM__PROMPT`                        |
| `proxy`       | 代理地址                                                |
| `stream`      | 是否流式请求，留空时回退到 `LLM__STREAM`                |
| `max_tokens`  | 最大输出 token 数（`anthropic` 必填，默认 4096）        |
| `temperature` | 采样温度                                                |
| `timeout`     | 非流式请求超时时间（秒）                                |
| `extra_body`  | 附加到请求体的额外字段，用于传各服务商特有参数          |
| `quota`       | 该模型的额度查询配置，留空时不支持 `/llm quota`         |

### 额度查询配置

`quota.provider` 决定额度接口的请求和响应格式，目前支持：

DeepSeek 字段与鉴权方式以[官方余额接口文档](https://api-docs.deepseek.com/zh-cn/api/get-user-balance)为准。

| Provider   | 追加路径        | 说明                                                           |
| ---------- | --------------- | -------------------------------------------------------------- |
| `deepseek` | `/user/balance` | 请求 DeepSeek 官方余额接口；默认复用模型 `api_key`             |
| `aperture` | `/api/quotas`   | 请求 Tailscale Aperture 额度接口；可用 `bucket` 筛选单个额度桶 |

未设置 `quota.api_url` 时，插件优先使用 `LLM__BASE_URL` 并追加上表路径；全局地址也为空时，
再使用模型解析后的服务地址。`quota.api_url` 可填写完整地址以覆盖这一行为。两种 provider 还可单独设置
`api_key`、`proxy` 与 `timeout`。

## 内置工具

| 工具                   | 说明                                          |
| ---------------------- | --------------------------------------------- |
| `query_weather`        | 查询现实城市或最终幻想 XIV 艾欧泽亚地区的天气 |
| `query_holiday_status` | 查询今天、周末、最近节假日以及调休安排        |

## 注册工具

在自己的模块中向注册表登记工具，模型即可按需调用：

```python
from src.plugins.llm.tools import registry


@registry.register("query_example", "查询示例数据")
async def query_example(name: str) -> str:
    """查询示例数据

    Args:
        name: 查询名称
    """
    return f"{name} 的查询结果"
```

参数 schema 由函数签名与 docstring 的 `Args` 小节自动生成，无默认值的参数为必填。
