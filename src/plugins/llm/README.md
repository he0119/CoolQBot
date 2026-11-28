# 大模型对话插件

接入多种大模型 API，提供智能对话与问答功能。

## 支持的 API 格式

| 格式                      | 请求地址                      | 认证方式                | 适用服务                              |
| ------------------------- | ----------------------------- | ----------------------- | ------------------------------------- |
| `openai_chat_completions` | `{base_url}/chat/completions` | `Authorization: Bearer` | DeepSeek、OpenAI 兼容接口、硅基流动等 |
| `openai_responses`        | `{base_url}/responses`        | `Authorization: Bearer` | OpenAI Responses API                  |
| `anthropic_messages`      | `{base_url}/v1/messages`      | `x-api-key`             | Anthropic Claude                      |

三种格式在请求结构上差异较大（system 提示词的位置、工具定义的嵌套层级、图片编码方式、
用量字段名各不相同），插件内部统一归一化，命令与配置的使用方式完全一致。

当前版本仍兼容旧名称 `chat`、`responses` 和 `anthropic`，加载配置时会输出弃用警告；
这些旧名称将在下个版本移除，请尽快改用表中的完整协议名。

## 功能

- 单轮与多轮对话，多轮支持「结束」「回滚」指令
- 群聊中直接 @ 机器人即可使用默认模型对话
- 流式与非流式请求
- 生图模型：可以是只能生图的 `openai_images` 模型，也可以是既能对话又能生图的 `openai_responses` 模型；生成结果直接发送为聊天图片
- `/draw <描述>` 使用本群启用的生图模型直接绘图，可指定格式、尺寸和宽高比，也可在支持的模型上用参考图改图
- 推理内容以引用块展示（DeepSeek 的 `reasoning_content`、Anthropic 的 `thinking`、Responses 的推理摘要）
- 使用 emoji reaction 反馈响应状态（思考中、已完成、失败）；QQ 适配器开始处理时改发普通消息，其他不支持的平台自动跳过
- `/chat` 默认不发送工具定义，增加 `-a|--agent` 后开放全部已注册工具；`/agent` 是 `/chat -a` 的快捷入口
- 超级管理员可用内置选项 `/chat --shortcut /ds _` 把常用命令（包括 `--model`）固化成 `/ds <内容>` 这样的快捷命令
- 工具调用（function calling）适配三种 API 格式；耗时较长时定期提示模型请求与工具调用进度
- 默认提供最终幻想 XIV 国服物价、时尚品鉴和 FFLogs 角色排名查询工具
- 模型默认声明 `text` 能力；图片输入需要额外声明 `vision`，也可将模型配置为仅视觉能力
- 超级管理员可按群启用或禁用模型，群管理员可分别设置默认对话、`zssm` 解释和视觉模型；未指定视觉模型时自动选择首个已启用且支持视觉的模型
- 内置“这是什么”解释模式，可解释被回复的文字、图片、网页与 PDF
- 所有大模型入口仅在群聊、频道等非私聊会话中生效
- 在回复末尾分行显示实际模型链、整轮耗时和带千分位的 token 用量，工具调用产生的多次请求会累计统计
- QQ 平台可优先发送原生 Markdown，其他平台或发送失败时自动回退
- Markdown 转图片
- TTS 语音回复（GPT-SoVITS）
- 按模型查询剩余额度，支持 Tailscale Aperture 与 DeepSeek 官方余额接口

## 请求标识

大模型请求会发送以下标识头：

- `User-Agent: CoolQBot/<当前版本>`：版本读取自 `pyproject.toml` 的 `[project].version`。
- `X-Session-Affinity: <随机会话 ID>`：每次创建 LLM 对话上下文时生成；同一轮工具调用和多轮对话保持一致，新的 `/chat` 或 `/agent` 调用会重新生成。不会发送群号或用户 ID。

## 命令

| 命令                                  | 别名              | 说明                      | 权限       |
| ------------------------------------- | ----------------- | ------------------------- | ---------- |
| `/chat <内容>`                        | -                 | 与模型对话                | 所有人     |
| `/chat --model <模型名> <内容>`       | -                 | 本次使用指定模型          | 所有人     |
| `/chat -c <内容>`                     | -                 | 启用多轮对话              | 所有人     |
| `/chat -r <内容>`                     | -                 | 把回复渲染成图片          | 所有人     |
| `/chat -t <内容>`                     | -                 | 使用语音回复              | 所有人     |
| `/chat -a <内容>`                     | `/agent <内容>`   | 使用全部工具完成问答      | 所有人     |
| `/chat -a --model <模型名> <内容>`    | `/agent --model`  | 指定模型进行工具问答      | 所有人     |
| `/chat -i <内容>`                     | -                 | 允许模型按需生图          | 所有人     |
| `/draw <描述>`                        | `/chat -d`        | 用本群生图模型生成图片    | 所有人     |
| `/draw -c <描述>`                     | -                 | 用同一 Responses 模型续画 | 所有人     |
| `/draw --image-model <模型名> <描述>` | `/draw --model`   | 本次指定生图模型          | 所有人     |
| `/<快捷指令名> [选项] <内容>`         | -                 | 用已注册的快捷命令对话    | 所有人     |
| `/llm model list`                     | -                 | 查看本群已启用模型        | 所有人     |
| `/llm model list --all`               | -                 | 查看全部模型及启用状态    | 超级管理员 |
| `/llm model list --capabilities`      | -                 | 查看模型用途及能力        | 所有人     |
| `/llm model set <模型名>`             | -                 | 设置群组默认模型          | 群管理员   |
| `/llm model set-zssm <模型名>`        | -                 | 设置群组解释模型          | 群管理员   |
| `/llm model clear-zssm`               | -                 | 解释模型跟随默认模型      | 群管理员   |
| `/llm model set-zssm-vision <模型名>` | -                 | 设置群组解释视觉模型      | 群管理员   |
| `/llm model clear-zssm-vision`        | -                 | 视觉模型恢复自动选择      | 群管理员   |
| `/llm model set-image <模型名>`       | -                 | 设置本群生图模型          | 群管理员   |
| `/llm model clear-image`              | -                 | 生图模型恢复自动选择      | 群管理员   |
| `/llm model enable <模型名...>`       | -                 | 启用一个或多个群组模型    | 超级管理员 |
| `/llm model enable --all`             | -                 | 启用群组全部模型          | 超级管理员 |
| `/llm model disable <模型名...>`      | -                 | 禁用一个或多个群组模型    | 超级管理员 |
| `/llm model disable --all`            | -                 | 禁用群组全部模型          | 超级管理员 |
| `/llm tts list`                       | -                 | 查看可用 TTS 模型列表     | 所有人     |
| `/llm tts set <模型名>`               | -                 | 设置群组默认 TTS 模型     | 群管理员   |
| `/llm quota [模型名]`                 | `/quota`、`/额度` | 查询模型剩余额度          | 所有人     |
| `/llm quota --all`                    | `/quota --all`    | 查询本群全部模型额度      | 所有人     |
| `@机器人 [选项] <内容>`               | -                 | 快捷发起纯对话            | 所有人     |
| `@机器人 -a <内容>`                   | -                 | 快捷启用工具增强模式      | 所有人     |
| `zssm [关注点]`                       | -                 | 解释输入或被回复内容      | 所有人     |
| `zssm -a [关注点]`                    | -                 | 启用工具增强解释          | 所有人     |
| `zssm -r [关注点]`                    | -                 | 将解释渲染为图片          | 所有人     |
| `zssm --model <模型名> [关注点]`      | -                 | 本次使用指定解释模型      | 所有人     |

对话、解释和绘图的选项应写在内容前，放在后面可能被当作正文。`/chat` 支持 `--model`、`-c`、`-r`、`-t`、
`-a|--agent`、`-i|--image` 和 `-d|--draw`。`/agent` 相当于 `/chat -a`，`/draw` 相当于 `/chat -d`。
@ 对话支持相同选项，`zssm` 可用 `--model`、`-r|--render` 和 `-a|--agent`。

`/llm model list` 对所有人都只显示本群已启用的模型及其“默认对话”、`zssm`、`zssm 视觉`和“生图”用途标签，并分区列出对话与群组设置命令；超级管理员增加 `--all` 后才会看到全局全部模型及本群启用状态。增加 `--capabilities` 后，当前列表才会同时显示每个模型的能力（文本、视觉、绘图），两个参数可以组合使用。
`/chat --shortcut` 注册的快捷命令与 `/chat` 同源：其后的选项按对话选项解析，目标模型仍受本群启用列表限制，详见「模型快捷命令」。快捷命令名注册在命令解析层，是进程级全局的，所有群共用同一批名字，群之间的差异只体现在可用模型上。
所有命令、快捷命令、`zssm` 和 @ 对话仅支持群聊、频道等非私聊会话；私聊消息不会触发大模型。

## 使用方法

### 基础对话

```bash
/chat 帮我写一段冒泡排序         # 与默认模型对话
/chat 这张图是什么               # 附带图片时会一起发给模型
/chat -a 查询成都今天的天气      # 允许模型调用工具（/agent 是等价快捷写法）
/chat -i 给这段故事配一张插图    # 允许模型按需调用本群生图模型
/draw 画一只戴围巾的猫          # 用本群生图模型生成图片
```

### 指定模型

```bash
/llm model list                  # 查看有哪些模型
/chat --model claude 讲个笑话    # 本次使用 claude
/llm model enable claude         # 为本群启用 claude
/llm model disable claude        # 为本群禁用 claude
/llm model set claude            # 之后本群默认使用 claude
/llm model set-zssm deepseek     # 本群 zssm 固定使用 deepseek
/llm model set-zssm-vision gpt   # 本群 zssm 需要时用 gpt 理解图片
/llm quota                       # 查询本群当前模型的剩余额度
/llm quota deepseek              # 查询指定模型的剩余额度
/llm quota --all                 # 查询本群已启用的全部模型额度
/quota deepseek                  # 使用快捷命令查询指定模型的剩余额度
@机器人 --model claude 讲个笑话  # @ 对话也可临时指定模型
@机器人 -a 查询成都今天的天气    # @ 对话按次启用全部工具
```

### 模型快捷命令

`--shortcut` 是 Alconna 的内置选项，只在 `chat` 命令上向超级管理员开放；它把**最近一次成功解析的对话命令**原样固化成快捷命令，因此可以把 `--model`、`-c`、`-r` 等选项一起带上：

```bash
/chat --model deepseek              # ① 先执行一次只带选项、不带正文的命令
/chat --shortcut /ds _              # ② 把上一条命令注册成 /ds
/ds 你好                            # ③ 之后 /ds 默认使用 deepseek
/ds -a 查询成都今天的天气            # 快捷命令后的选项仍按对话选项解析
```

快捷命令名要**带上命令前缀**（`/ds`），否则只能匹配不带前缀的 `ds 你好` 写法；`COMMAND_START` 配置了多个前缀时，每个前缀都要单独注册一次。其他内置子参数：

| 参数                          | 说明                                       |
| ----------------------------- | ------------------------------------------ |
| `/chat --shortcut list`       | 查看当前已注册的快捷命令                   |
| `/chat --shortcut delete /ds` | 删除指定快捷命令                           |
| `/chat --shortcut /ds _`      | 使用最近一次命令注册（选项一并保留）       |
| `/chat --shortcut /ds $`      | 只注册当前命令本身，不带最近一次命令的选项 |
| `/chat --shortcut /ds chat`   | 指向该命令本身，相当于 `/chat` 的别名      |

限制：

- 目标模型仍需在本群启用，否则会提示“本群未启用的模型”。
- 快捷命令与命令一样允许模糊匹配：`/ds你好` 与 `/ds 你好` 等价，但 `/dsx 你好` 会被解析成 `/ds` 加上正文 `x 你好`。
- 快捷命令注册在命令解析层，因此是进程级全局的、无法按群分别设置名字；注册结果只存在于内存中，**重启机器人后失效**，需要重新注册。

### 多轮对话

```bash
/chat -c 我们来玩成语接龙
# 之后直接发消息继续对话
# 发送「结束」结束对话，「回滚」撤销上一轮
```

### 图片与语音

```bash
/chat -r 用表格对比 Python 和 Go # 回复渲染成图片
/chat -a 查询 Python 3.14 新特性 # 工具增强模式可以搜索网页
/agent 查一下静语庄园的萨维奈舞裙价格 # 快捷启用工具并调用 FF14 物价工具
/llm tts set 派蒙                # 设置语音模型
/chat -t 念一首诗                # 用语音回复
```

### 绘图与改图

本群启用至少一个生图模型后，即可用 `/draw` 或 `/chat -d` 画图，无需启用聊天模型。
`/chat -i` 允许聊天模型按需调用生图，单轮最多一次。生图会产生额外费用，`/chat -a` 只有同时使用 `-i` 才开放生图。

```text
/draw 画一只猫
/draw --image-model painter 画一张白底贴纸
/draw --format webp --size 1536x1024 画一张横幅
/draw --format gif --frames 12 --size auto 画一个循环挥手的角色
```

`--image-model` 按配置名选择本次生图模型。直接绘图时，旧选项 `--model` 现在是它的别名。
在普通聊天中（包括 `/chat -i`），`--model` 仍然选择聊天模型。未显式选模型时，优先使用 `/llm model set-image`
为本群设置且满足本次要求的模型，否则按全局声明顺序从本群已启用的模型中选。回复会显示实际使用的配置名。

直接绘图也会从描述里读取输出要求。比如「画一张 960 像素见方的动态贴纸」会请求 960×960 的多帧 GIF，
「输出 1536×1024 的 WebP 横幅」会请求指定的格式和尺寸。支持 GIF、PNG、JPEG 和 WebP，以及 `16:9`、
`9:16`、`4:3` 等宽高比。只指定比例时按模型默认尺寸的短边换算，默认是 `auto` 或没设置时取 1024 像素。

静态方图的「高清 / HD」目标是 2880×2880。描述同时有「高清」和宽高比时，以 2880 为短边目标。
OpenAI 官方 GPT-Image-2.6 Sunburst 或 Flare 直连时，插件会把换算结果对齐到 16 像素，并按接口尺寸上限调整高清图。
例如普通 `16:9` 在短边目标为 1024 时请求 `1824x1024`，高清 `16:9` 请求 `3840x2160`。

明确写出的像素尺寸会原样提交。描述同时指定宽高和比例时，两者须一致。`--format`、`--size`、`--hd` 等
选项优先于描述里的对应要求。描述中的明确像素尺寸优先于「高清」。引号里的文字和「动态光影」等风格词不作为输出要求。
要求冲突或没有满足条件的模型时，机器人会在请求图片前提示。返回的图片不符合要求时，机器人会提示原因，且不会自动重画。

用 OpenAI 官方 GPT-Image-2.6 Sunburst 或 Flare 直连生成 GIF 时，可用 `--frames` 或描述里的「12 帧 GIF」指定帧数，范围是 2–16 帧。
指定帧数时会核验实际返回的帧数。官方高清 GIF 未指定像素尺寸时使用 `size=auto`，由服务决定像素尺寸。
若指定了宽高比，机器人仍会检查返回图片的比例。动图能否播放取决于聊天平台。

使用 OpenAI 官方 GPT-Image-2.6 Sunburst 或 Flare 直连时，可以回复或附上静态 PNG、JPEG 或 WebP，
再发送 `/draw 把背景改成蓝色` 来用参考图改图。每次改图时回复要改的图片即可。
`/draw -c` 用于同一个 Responses 生图模型的多轮续画。

管理员配置见下文的[生图模型配置](#生图模型配置)。

### 解释消息内容

直接发送 `zssm <内容>` 可以解释一段文字。更常用的方式是回复群友消息并发送 `zssm`，命令后的文字会作为关注点：

```text
群友：量子纠缠说明两个粒子可以超光速通信……
你（回复群友）：zssm 重点说明“超光速通信”是否准确
你（回复群友）：zssm -a 核查这条消息是否符合最新资料
你（回复群友）：zssm -r 用图片排版解释结果
你（回复群友）：zssm --model claude 重点说明“超光速通信”是否准确
```

`--model` 只覆盖本次解释，不会修改群组设置。`-r|--render` 将本次解释的 Markdown 回复渲染为图片，渲染失败时自动回退为文字。未通过 `/llm model set-zssm` 单独设置解释模型时，`zssm` 跟随本群默认模型；`/llm model clear-zssm` 可恢复这一行为。解释模式使用独立提示词且不展示推理过程；默认不开放工具，显式增加 `-a|--agent` 后会为本次解释开放包括 `web_search` 在内的全部工具。机器人的回答引用你发送的 `zssm` 命令。

图片处理取决于模型能力：解释模型在 `capabilities` 中声明 `vision` 时，图片直接随解释请求发送，只调用一次；否则优先使用 `/llm model set-zssm-vision` 显式指定的模型，未指定时按全局模型配置顺序自动选择本群首个已启用且声明了 `vision` 的模型，先生成图片描述再解释。`/llm model clear-zssm-vision` 会清除显式选择并恢复自动选择；没有符合条件的模型时会给出明确提示。

超级管理员使用 `/llm model enable <模型名...>` 为本群增量启用一个或多个模型，使用 `/llm model disable <模型名...>` 增量禁用；两个命令都可增加 `--all` 操作全部模型，但不能同时指定具体模型。未设置过的群默认不启用任何模型。默认模型、临时 `--model`、额度查询以及 `zssm` 的解释和视觉模型都不能越过该列表。禁用正在使用的模型时，默认模型会切换到剩余列表第一项，解释和显式视觉模型设置会被清除，视觉模型随后从剩余列表中重新自动选择。

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

通过 `LLM__` 前缀在 `.env` 中配置。`models` 的第一项为默认模型，以下示例默认使用 `gpt-6.1-sol`。
已有群组可先执行 `/llm model enable gpt`，再通过 `/llm model set gpt` 切换默认模型。
快捷对话只过滤 `COMMAND_START` 中的非空前缀；如果命令配置了空前缀，未带前缀的命令无法与普通对话可靠区分。

```env
# 全局服务地址，未单独配置服务地址的模型都用它
LLM__BASE_URL=https://api.example.com
# 全局密钥，未单独配置密钥的模型都用它
LLM__API_KEY=sk-xxx
# 全局人设
LLM__PROMPT=你是一个乐于助人的助手
# 是否展示推理内容
LLM__SEND_THINKING=true
# 是否在 QQ 平台优先发送原生 Markdown；显式使用 /chat -r 时仍发送图片
LLM__PREFER_MARKDOWN=false
# 是否默认把回复渲染成图片
LLM__MD_TO_PIC=false
# 是否响应群聊 @ 等被适配器判定为发给机器人的消息
LLM__RESPOND_TO_MENTION=true
# 是否流式请求
LLM__STREAM=false
# 单次提问允许的最大模型请求次数；Agent 会提前获知预算，最后一次请求禁止工具调用并基于已有结果收尾
LLM__MAX_REQUESTS=10
# Agent 首次模型请求开始后的等待提示延迟，以及后续重复提示的间隔（秒）
LLM__REQUEST_NOTICE_DELAY=20
LLM__REQUEST_NOTICE_INTERVAL=30
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
    "name": "gpt",
    "provider": "openai_responses",
    "model": "gpt-6.1-sol",
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-openai-xxx",
    "capabilities": ["text", "vision"]
  },
  {
    "name": "painter",
    "provider": "openai_images",
    "model": "gpt-image-2.5-sunburst",
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-openai-xxx",
    "capabilities": ["image_generation"],
    "timeout": 300,
    "extra_body": {
      "size": "1024x1024",
      "quality": "high",
      "output_format": "png"
    }
  },
  {
    "name": "deepseek",
    "provider": "openai_chat_completions",
    "model": "deepseek-chat",
    "quota": {
      "provider": "deepseek"
    }
  },
  {
    "name": "deepseek-aperture",
    "provider": "openai_chat_completions",
    "model": "deepseek-chat",
    "base_url": "https://ai.example.com/v1",
    "quota": {
      "provider": "aperture",
      "bucket": "deepseek"
    }
  },
  {
    "name": "claude",
    "provider": "anthropic_messages",
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

模型能做什么只看 `capabilities` 的声明：声明了 `text` 才能对话，声明了 `vision` 才能看图，声明了 `image_generation` 才能被设为生图模型。省略时默认为 `["text"]`（`openai_images` 接口省略时默认为 `["image_generation"]`）。普通多模态模型应配置为 `["text", "vision"]`；配置为 `["vision"]` 的模型只参与 zssm 图片理解，不会被选为默认对话、临时文本对话或 zssm 解释模型。

加载配置时会检查声明是否和接口匹配，不匹配直接报错：`openai_images` 接口只能生图，只能声明 `image_generation`；`image_generation` 目前只支持 `openai_images` 和 `openai_responses` 两种接口。既能对话又能生图的模型请用 `openai_responses` 并同时声明 `text` 和 `image_generation`。

### 单个模型的可配置项

| 字段           | 说明                                                                           |
| -------------- | ------------------------------------------------------------------------------ |
| `name`         | 模型标识，命令中用此名称选择模型                                               |
| `model`        | 传给 API 的模型名，留空时与 `name` 相同                                        |
| `provider`     | API 格式，三种对话协议，或只能生图的 `openai_images`                           |
| `base_url`     | 服务地址，留空时回退到 `LLM__BASE_URL`                                         |
| `api_key`      | 密钥，留空时回退到 `LLM__API_KEY`                                              |
| `prompt`       | 人设，留空时回退到 `LLM__PROMPT`                                               |
| `proxy`        | 代理地址                                                                       |
| `stream`       | 是否流式请求，留空时回退到 `LLM__STREAM`                                       |
| `max_tokens`   | 最大输出 token 数（`anthropic` 必填，默认 4096）                               |
| `temperature`  | 采样温度                                                                       |
| `timeout`      | 非流式请求超时时间（秒）                                                       |
| `extra_body`   | 附加到请求体的额外字段，用于传各服务商特有参数                                 |
| `capabilities` | 模型能力列表，默认 `text`；可选 `text`、`vision`、`image_generation`（可生图） |
| `quota`        | 该模型的额度查询配置，留空时不支持 `/llm quota`                                |

### OpenAI Responses

使用 OpenAI 官方接口时，`provider` 设为 `openai_responses`，`base_url` 设为
`https://api.openai.com/v1`。`model` 填写账号可用的模型 ID；推理强度、推理摘要和文本详细程度
可通过 `extra_body.reasoning`、`extra_body.text` 配置，具体取值取决于所选模型。
`max_tokens` 会转换为 `max_output_tokens`，包含推理 token；`temperature` 留空时不发送。

插件在本地维护完整上下文，Responses 默认发送 `store: false`，并请求加密推理数据以兼容旧版
接口；后续请求保留原始输出中的加密推理、助手 `phase` 和图片生成结果。可通过 `extra_body`
显式覆盖 `store`、`include` 等字段。接入方式参考 OpenAI 的
[Responses 迁移指南](https://developers.openai.com/api/docs/guides/migrate-to-responses)、
[推理上下文说明](https://developers.openai.com/api/docs/guides/reasoning)和
[图片生成工具文档](https://developers.openai.com/api/docs/guides/tools-image-generation)。

`extra_body.tools` 中配置的原生工具可用于普通 `/chat`，原生图片工具仅用于生图请求。
`-a|--agent` 会额外传入插件注册的函数工具。模型请求次数达到上限时，`tool_choice: "none"` 会禁用工具。

### 生图模型配置

图片由本群的**生图模型**生成，有两种配置方式。

- 只能生图的模型，例如 `gpt-image-2.5-sunburst`，使用 `openai_images`，可省略 `image_generation` 能力声明。
  参考上方 `painter` 示例，在 `extra_body` 里配置质量、输出格式等默认值。
- 同时支持对话和生图的模型使用 `openai_responses`，同时声明 `text` 和 `image_generation`。
  生图请求使用该模型配置的服务地址和原生 `image_generation` 工具。

超级管理员可用 `/llm model enable painter` 为本群启用模型。群管理员可用 `/llm model set-image <模型名>`
设为本群首选生图模型，或用 `/llm model clear-image` 恢复自动选择。
`/llm model list --capabilities` 会显示支持绘图的模型。

使用 `image_output_formats` 和 `image_sizes` 声明服务支持的格式和尺寸，用 `image_sizes_by_format`
单独限制某个格式。`extra_body.output_format` 和 `extra_body.size` 中的默认值也可作为支持声明。
直连 `https://api.openai.com/v1` 的 GPT-Image-2.6 Sunburst 或 Flare 可按[官方像素限制](https://developers.openai.com/api/docs/guides/image-generation#customize-image-output)
使用 PNG、JPEG 和 WebP，无需逐个列出静态图尺寸。管理员显式配置的格式和尺寸范围仍然有效。

#### 官方 GIF 配置

官方 GPT-Image-2.6 Sunburst 或 Flare 直连时，管理员需确认项目已取得 GIF 预览权限，并启用 `gif` 格式。
可由服务选择默认尺寸和帧数。

```json
{
  "image_output_formats": ["png", "gif"],
  "extra_body": { "size": "auto" }
}
```

用户与管理员都未指定帧数时，请求不发送 `frame_count`，使用服务默认的 9 帧。
`image_gif_size_presets` 可指定普通 GIF 的候选默认尺寸。用户明确指定 `--size 3200x1440` 等尺寸时，
尺寸不受候选默认尺寸限制，但须符合服务的帧尺寸规则及管理员设置的尺寸范围。
服务会检查帧数和整组图片的总像素上限。失败时不会换尺寸重试。
通过其他网关接入同名模型时，其 GIF 能力和权限取决于网关。

#### Responses 图片工具

Responses 生图保留图片工具已配置的标准参数 `size`、`quality`、`background`、`output_format`、
`output_compression`、`moderation` 和 `action`。GIF 动画参数不发送到标准 Responses。
普通聊天请求会移除原生图片生成工具。启用 `/chat -i` 时，聊天通过所选生图模型自身的连接请求图片。

PNG、JPEG、WebP 和 GIF 会作为原图发送，只有图片时也会附带统计。流式请求等待最终图片，不发送中间预览。

### 额度查询配置

`quota.provider` 决定额度接口的请求和响应格式，目前支持：

DeepSeek 字段与鉴权方式以[官方余额接口文档](https://api-docs.deepseek.com/zh-cn/api/get-user-balance)为准。

| Provider   | 接口根路径      | 说明                                                           |
| ---------- | --------------- | -------------------------------------------------------------- |
| `deepseek` | `/user/balance` | 请求 DeepSeek 官方余额接口；默认复用模型 `api_key`             |
| `aperture` | `/api/quotas`   | 请求 Tailscale Aperture 额度接口；可用 `bucket` 筛选单个额度桶 |

未设置 `quota.api_url` 时，插件优先使用 `LLM__BASE_URL` 的域名根目录解析上表路径；例如
`https://ai.example.com/v1` 会解析为 `https://ai.example.com/api/quotas`。全局地址为空时，再使用模型解析后的
服务地址。额度接口位于其他域名或非标准路径时，可用完整的 `quota.api_url` 覆盖。两种 Provider 还可单独设置
`api_key`、`proxy` 与 `timeout`。

使用 `/llm quota --all` 时，只查询本群已启用的模型。URL、鉴权、代理和超时均相同的额度请求会合并为一次，
不同请求并发执行；共享同一额度视图（例如相同 Aperture `bucket`）的模型也会合并显示。单个接口查询失败不会
中断其他模型的结果。

## 内置工具

| 工具                             | 说明                                          |
| -------------------------------- | --------------------------------------------- |
| `query_weather`                  | 查询现实城市或最终幻想 XIV 艾欧泽亚地区的天气 |
| `query_holiday_status`           | 查询今天、周末、最近节假日以及调休安排        |
| `web_search`                     | 搜索互联网，返回标题、URL 与摘要              |
| `web_fetch`                      | 安全读取网页、文本、JSON 或 PDF 正文          |
| `query_ff14_item_price`          | 查询国服服务器或大区的物品市场价格            |
| `query_ff14_fashion_report`      | 查询本周时尚品鉴满分攻略                      |
| `query_fflogs_character_ranking` | 查询国服角色的 FFLogs 副本排名                |

普通 `/chat`、@ 对话和 `zssm` 不会发送任何工具定义；带 `-a|--agent` 的调用会发送全部已注册工具，`/agent` 是 `/chat -a` 的快捷写法。
`web_search` 使用 `ddgs` 搜索并限制单次结果数；
模型需要详细内容时，可继续调用 `web_fetch` 读取搜索结果。
`web_fetch` 只接受 HTTP(S) URL，会校验每次重定向并拒绝本机、内网和其他非公网地址，同时限制下载大小、
PDF 页数和提取字符数。两项工具返回的内容都带有“不可信外部数据”标记，来源 URL 会一并交给模型。

三个最终幻想 XIV 工具随 `/chat -a`（或快捷写法 `/agent`）提供：物价查询默认使用猫小胖大区，也可以显式指定国服服务器或大区；
时尚品鉴返回当前攻略及来源链接；FFLogs 角色排名需要配置 `FFLOGS_TOKEN`，并显式提供副本、角色名和服务器名。

旧版 `LLM__ZSSM_MAX_RESOURCE_BYTES`、`LLM__ZSSM_MAX_RESOURCE_CHARS`、`LLM__ZSSM_MAX_PDF_PAGES`、
`LLM__ZSSM_RESOURCE_TIMEOUT`、`LLM__ZSSM_RESOURCE_PROXY` 与 `LLM__ZSSM_RESOURCE_FAKE_IP_RANGES`
仍作为上述通用 Web 配置的兼容别名，无需立即修改已有部署。

## 注册工具

在自己的模块中向注册表登记工具，模型即可按需调用。导入注册表前先用 `require` 声明依赖大模型插件，
保证它先于本插件加载（带子插件的插件在父插件的 `__init__.py` 里声明即可）：

```python
from nonebot import require

require("src.plugins.llm")
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
