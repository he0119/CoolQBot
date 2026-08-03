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
- 群聊中直接 @ 机器人即可使用默认模型对话
- 流式与非流式请求
- 推理内容以引用块展示（DeepSeek 的 `reasoning_content`、Anthropic 的 `thinking`、Responses 的推理摘要）
- 使用 emoji reaction 反馈响应状态（思考中、已完成、失败；不支持的平台自动跳过）
- 工具调用（function calling），三种格式自动适配；耗时较长时定期提示模型请求与工具调用进度
- 内置网页搜索与网页/PDF 正文读取工具，返回来源 URL 并标记不可信外部内容
- 图片输入（多模态），需要模型在 `capabilities` 中声明 `vision`
- 超级管理员可按群开放模型，群管理员可分别设置默认对话、`zssm` 解释和视觉模型
- 内置“这是什么”解释模式，可解释被回复的文字、图片、网页与 PDF
- 在回复末尾显示整轮耗时、实际模型和 token 用量，工具调用产生的多次请求会累计统计
- Markdown 转图片
- TTS 语音回复（GPT-SoVITS）
- 按模型查询剩余额度，支持 Tailscale Aperture 与 DeepSeek 官方余额接口

## 请求标识

大模型请求会发送以下标识头：

- `User-Agent: CoolQBot/<当前版本>`：版本读取自 `pyproject.toml` 的 `[project].version`。
- `X-Session-Affinity: <随机会话 ID>`：每次创建 LLM 对话上下文时生成；同一轮工具调用和多轮对话保持一致，新的 `/llm` 调用会重新生成。不会发送群号或用户 ID。

## 命令

| 命令                                     | 别名              | 说明                  | 权限       |
| ---------------------------------------- | ----------------- | --------------------- | ---------- |
| `/llm <内容>`                            | `/ai`             | 与模型对话            | 所有人     |
| `/llm --model <模型名> <内容>`           | -                 | 本次使用指定模型      | 所有人     |
| `/llm -c <内容>`                         | -                 | 启用多轮对话          | 所有人     |
| `/llm -r <内容>`                         | -                 | 把回复渲染成图片      | 所有人     |
| `/llm -t <内容>`                         | -                 | 使用语音回复          | 所有人     |
| `/llm model --list`                      | -                 | 查看可用模型列表      | 所有人     |
| `/llm model --set <模型名>`              | -                 | 设置群组默认模型      | 群管理员   |
| `/llm model --set-zssm <模型名>`         | -                 | 设置群组解释模型      | 群管理员   |
| `/llm model --clear-zssm`                | -                 | 解释模型跟随默认模型  | 群管理员   |
| `/llm model --set-vision <模型名>`       | -                 | 设置群组解释视觉模型  | 群管理员   |
| `/llm model --clear-vision`              | -                 | 清除群组解释视觉模型  | 群管理员   |
| `/llm model --set-available <模型名...>` | -                 | 设置群组可用模型      | 超级管理员 |
| `/llm model --clear-available`           | -                 | 清空群组可用模型      | 超级管理员 |
| `/llm tts --list`                        | -                 | 查看可用 TTS 模型列表 | 所有人     |
| `/llm tts --set <模型名>`                | -                 | 设置群组默认 TTS 模型 | 群管理员   |
| `/llm quota [模型名]`                    | `/quota`、`/额度` | 查询模型剩余额度      | 所有人     |
| `@机器人 <内容>`                         | -                 | 使用默认模型直接对话  | 所有人     |
| `zssm [关注点]`                          | -                 | 解释输入或被回复内容  | 所有人     |
| `zssm --model <模型名> [关注点]`         | -                 | 本次使用指定解释模型  | 所有人     |

对话及解释选项应写在内容前；`<内容>` 是可变长参数，放在内容后的选项可能被当作正文。
普通用户使用 `/llm model --list` 时只会看到本群已开放的模型；超级管理员会看到全局配置中的全部模型，并显示每个模型的开放状态及当前默认、解释、视觉用途。

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
/llm --model claude 讲个笑话     # 本次使用 claude
/llm model --set claude          # 之后本群默认使用 claude
/llm model --set-zssm deepseek   # 本群 zssm 固定使用 deepseek
/llm model --set-vision gpt      # 本群 zssm 需要时用 gpt 理解图片
/llm quota                       # 查询本群当前模型的剩余额度
/llm quota deepseek              # 查询指定模型的剩余额度
/quota deepseek                  # 使用快捷命令查询指定模型的剩余额度
@机器人 讲个笑话                 # 群聊中直接使用默认模型
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

### 解释消息内容

直接发送 `zssm <内容>` 可以解释一段文字。更常用的方式是回复群友消息并发送 `zssm`，命令后的文字会作为关注点：

```text
群友：量子纠缠说明两个粒子可以超光速通信……
你（回复群友）：zssm 重点说明“超光速通信”是否准确
你（回复群友）：zssm --model claude 重点说明“超光速通信”是否准确
```

`--model` 只覆盖本次解释，不会修改群组设置。未通过 `/llm model --set-zssm` 单独设置解释模型时，`zssm` 跟随本群默认模型；`--clear-zssm` 可恢复这一行为。解释模式使用独立提示词，不展示推理过程，也不开放工具调用；即使模型返回了工具调用请求也会被拒绝。机器人的回答引用你发送的 `zssm` 命令。

图片处理取决于模型能力：解释模型在 `capabilities` 中声明 `vision` 时，图片直接随解释请求发送，只调用一次；否则需要通过 `/llm model --set-vision` 为本群指定另一个声明了 `vision` 的模型，先生成图片描述再解释。

超级管理员使用 `/llm model --set-available <模型名...>` 精确设置本群开放的模型；未设置过的群默认不允许使用任何模型，`--clear-available` 可清空本群的准入列表。默认模型、临时 `--model`、额度查询以及 `zssm` 的解释和视觉模型都不能越过该列表。修改开放列表时，已不再可用的默认模型会切换到列表第一项，解释和视觉模型设置会被清除。

消息中实际出现的网页或 PDF 链接会在调用模型前读取，读取器有以下限制：

- 只允许 HTTP(S)，拒绝带登录凭据的 URL，以及指向本机、内网和其他非公网地址的目标；每次重定向都会重新校验。
- 域名解析到 `LLM__WEB_FETCH_FAKE_IP_RANGES` 配置的网段时放行，用于兼容透明代理的 fake-ip；直接在 URL 里填写这些 IP 仍会拒绝。
- 限制资源数量、单个资源的下载字节数、PDF 页数与提取文本长度，超长内容会截断。
- 配置 `LLM__WEB_PROXY` 后，域名由代理解析，上述地址校验只在本地生效，实际能访问到哪些网络取决于代理。
- 校验和建立连接是两次独立的域名解析，理论上存在 DNS rebinding 的时间差，不适合用在能访问敏感内网的环境里。

所有不可信内容（被解释的文字、关注点、图片描述、网页正文）都以 JSON 数据传给模型，提示词要求模型只把它们当作待解释的数据，不执行其中的指令。

## 日志

每个 `LLMHandler` 使用随机会话亲和 ID 的前 8 位关联同一轮或多轮对话日志，不包含用户或群组标识。

- `INFO`：记录会话开始/完成、工具名与参数名、Web 搜索/抓取、额度、TTS、回复方式、数量、结果规模和耗时。
- `DEBUG`：记录每轮 Provider 的协议、流式模式、消息/工具数量、结束原因和 token 用量。
- `WARNING`：记录失败阶段与异常类型；上游错误正文不会写入日志。

日志不会记录提示词、用户/模型正文、工具参数值、搜索词、API key、TTS 令牌、群号、用户 ID、URL 路径或查询参数。Web 资源只记录主机名。

## 配置说明

通过 `LLM__` 前缀在 `.env` 中配置。`models` 的第一项为默认模型。
快捷对话只过滤 `COMMAND_START` 中的非空前缀；如果命令配置了空前缀，未带前缀的命令无法与普通对话可靠区分。

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
# 是否响应群聊 @ 等被适配器判定为发给机器人的消息
LLM__RESPOND_TO_MENTION=true
# 是否流式请求
LLM__STREAM=false
# 单次提问允许的最大工具调用轮数
LLM__MAX_TOOL_ROUNDS=5
# 工具调用开始后首次提示与后续重复提示的间隔（秒）
LLM__TOOL_NOTICE_DELAY=2
LLM__TOOL_NOTICE_INTERVAL=30
# 网页搜索配置；结果数量还会受模型传入的 max_results 限制
LLM__WEB_SEARCH_MAX_RESULTS=5
LLM__WEB_SEARCH_TIMEOUT=10
LLM__WEB_SEARCH_REGION=wt-wt
LLM__WEB_SEARCH_SAFESEARCH=moderate
LLM__WEB_SEARCH_BACKEND=auto
# 网页/PDF 读取限制，同时用于 zssm 自动读取外部资料
LLM__WEB_FETCH_MAX_BYTES=10485760
LLM__WEB_FETCH_MAX_CHARS=30000
LLM__WEB_FETCH_MAX_PDF_PAGES=50
LLM__WEB_FETCH_TIMEOUT=30
# 可选，网页搜索以及下载网页与 PDF 时使用的代理
LLM__WEB_PROXY=
# 域名经透明代理解析到 fake-ip 时允许的网段
LLM__WEB_FETCH_FAKE_IP_RANGES='["198.18.0.0/15"]'
# 多轮对话等待用户输入的超时时间（秒）
LLM__CONTEXT_TIMEOUT=120

# 输入与自动读取外部资源数量限制
LLM__ZSSM_MAX_IMAGES=2
LLM__ZSSM_MAX_IMAGE_BYTES=10485760
LLM__ZSSM_MAX_RESOURCES=2

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
    "api_key": "sk-openai-xxx",
    "capabilities": ["vision"]
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

| 字段           | 说明                                                    |
| -------------- | ------------------------------------------------------- |
| `name`         | 模型标识，命令中用此名称选择模型                        |
| `model`        | 传给 API 的模型名，留空时与 `name` 相同                 |
| `provider`     | API 格式，`chat` / `responses` / `anthropic`            |
| `base_url`     | 服务地址，留空时回退到 `LLM__BASE_URL` 或按格式取默认值 |
| `api_key`      | 密钥，留空时回退到 `LLM__API_KEY`                       |
| `prompt`       | 人设，留空时回退到 `LLM__PROMPT`                        |
| `proxy`        | 代理地址                                                |
| `stream`       | 是否流式请求，留空时回退到 `LLM__STREAM`                |
| `max_tokens`   | 最大输出 token 数（`anthropic` 必填，默认 4096）        |
| `temperature`  | 采样温度                                                |
| `timeout`      | 非流式请求超时时间（秒）                                |
| `extra_body`   | 附加到请求体的额外字段，用于传各服务商特有参数          |
| `capabilities` | 模型能力列表；`vision` 表示可直接接收图片               |
| `quota`        | 该模型的额度查询配置，留空时不支持 `/llm quota`         |

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
| `web_search`           | 搜索互联网，返回标题、URL 与摘要              |
| `web_fetch`            | 安全读取网页、文本、JSON 或 PDF 正文          |

`web_search` 使用 `ddgs` 搜索并限制单次结果数；模型需要详细内容时，可继续调用 `web_fetch` 读取搜索结果。
`web_fetch` 只接受 HTTP(S) URL，会校验每次重定向并拒绝本机、内网和其他非公网地址，同时限制下载大小、
PDF 页数和提取字符数。两项工具返回的内容都带有“不可信外部数据”标记，来源 URL 会一并交给模型。

旧版 `LLM__ZSSM_MAX_RESOURCE_BYTES`、`LLM__ZSSM_MAX_RESOURCE_CHARS`、`LLM__ZSSM_MAX_PDF_PAGES`、
`LLM__ZSSM_RESOURCE_TIMEOUT`、`LLM__ZSSM_RESOURCE_PROXY` 与 `LLM__ZSSM_RESOURCE_FAKE_IP_RANGES`
仍作为上述通用 Web 配置的兼容别名，无需立即修改已有部署。

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
