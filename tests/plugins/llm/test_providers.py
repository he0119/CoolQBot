"""测试三种 API 格式的请求构造与响应解析"""

import json
import tomllib
from pathlib import Path

import httpx
import pytest
import respx
from nonebug import App
from respx import MockRouter

PROJECT_VERSION = tomllib.loads((Path(__file__).parents[3] / "pyproject.toml").read_text(encoding="utf-8"))["project"][
    "version"
]


def make_config(provider: str, **kwargs):
    """构造一个测试用的模型配置"""
    from src.plugins.llm.config import ModelConfig

    defaults = {
        "name": "test-model",
        "provider": provider,
        "base_url": "https://api.example.com",
        "api_key": "sk-test",
        "stream": False,
    }
    defaults.update(kwargs)
    return ModelConfig(**defaults)


def make_messages():
    """构造一段带 system 的对话"""
    from src.plugins.llm.schemas import Message

    return [
        Message(role="system", content="你是一个助手"),
        Message.user("你好"),
    ]


# ---------------------------------------------------------------- chat 格式


@respx.mock(assert_all_called=True)
async def test_chat_request_and_response(app: App, respx_mock: MockRouter):
    """chat 格式：system 是一条消息，用量字段为 prompt/completion_tokens"""
    from src.plugins.llm.providers import ChatProvider

    route = respx_mock.post("https://api.example.com/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "你好呀", "reasoning_content": "在想"},
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )
    )

    provider = ChatProvider(make_config("chat"))
    completion = await provider.chat(make_messages())

    request = route.calls[0].request
    payload = json.loads(request.content)
    assert request.headers["authorization"] == "Bearer sk-test"
    assert request.headers["user-agent"] == f"CoolQBot/{PROJECT_VERSION}"
    assert "x-session-affinity" not in request.headers
    # system 作为普通消息留在 messages 里
    assert payload["messages"][0] == {"role": "system", "content": "你是一个助手"}
    assert payload["messages"][1] == {"role": "user", "content": "你好"}
    assert payload["model"] == "test-model"

    assert completion.content == "你好呀"
    assert completion.reasoning == "在想"
    assert completion.finish_reason == "stop"
    assert completion.usage.input_tokens == 10
    assert completion.usage.output_tokens == 5


@respx.mock(assert_all_called=True)
async def test_chat_tools_and_images(app: App, respx_mock: MockRouter):
    """chat 格式：工具嵌套在 function 下，图片用 image_url + data URI"""
    from src.plugins.llm.providers import ChatProvider
    from src.plugins.llm.schemas import ImageContent, Message, ToolParam

    route = respx_mock.post("https://api.example.com/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {"name": "get_weather", "arguments": '{"city": "成都"}'},
                                }
                            ],
                        },
                    }
                ],
            },
        )
    )

    tools = [ToolParam(name="get_weather", description="查询天气", parameters={"type": "object", "properties": {}})]
    messages = [Message.user("天气", [ImageContent(data=b"fakeimage", mimetype="image/png")])]

    provider = ChatProvider(make_config("chat"))
    completion = await provider.chat(messages, tools)

    payload = json.loads(route.calls[0].request.content)
    assert payload["tools"][0]["function"]["name"] == "get_weather"
    content = payload["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "天气"}
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")

    assert completion.tool_calls[0].name == "get_weather"
    assert completion.tool_calls[0].arguments == {"city": "成都"}


def test_chat_reasoning_content_round_trip(app: App):
    """DeepSeek 工具回合需要原样回传 reasoning_content"""
    from src.plugins.llm.providers import ChatProvider
    from src.plugins.llm.schemas import Message

    provider = ChatProvider(make_config("chat"))
    completion = provider.parse_response(
        {
            "model": "test-model",
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "reasoning_content": "需要查询天气",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "get_weather", "arguments": '{"city":"成都"}'},
                            }
                        ],
                    },
                }
            ],
        }
    )

    payload = provider.build_payload([Message.user("天气"), completion.message, Message.tool("call_1", "晴")])

    assert payload["messages"][1]["reasoning_content"] == "需要查询天气"
    assert payload["messages"][1]["tool_calls"][0]["id"] == "call_1"


@respx.mock(assert_all_called=True)
async def test_chat_stream(app: App, respx_mock: MockRouter):
    """chat 格式：流式分片按 index 拼接，[DONE] 结束"""
    from src.plugins.llm.providers import ChatProvider

    chunks = [
        'data: {"model":"test-model","choices":[{"delta":{"reasoning_content":"想"}}]}\n\n',
        'data: {"model":"test-model","choices":[{"delta":{"content":"你"}}]}\n\n',
        'data: {"model":"test-model","choices":[{"delta":{"content":"好"},"finish_reason":"stop"}]}\n\n',
        'data: {"model":"test-model","choices":[],"usage":{"prompt_tokens":3,"completion_tokens":2}}\n\n',
        "data: [DONE]\n\n",
    ]
    route = respx_mock.post("https://api.example.com/chat/completions").mock(
        return_value=httpx.Response(200, text="".join(chunks))
    )

    provider = ChatProvider(make_config("chat", stream=True), session_affinity="test-affinity")
    completion = await provider.chat(make_messages())

    request = route.calls[0].request
    assert request.headers["user-agent"] == f"CoolQBot/{PROJECT_VERSION}"
    assert request.headers["x-session-affinity"] == "test-affinity"
    assert completion.content == "你好"
    assert completion.reasoning == "想"
    assert completion.finish_reason == "stop"
    assert completion.usage.output_tokens == 2


# ----------------------------------------------------------- responses 格式


@respx.mock(assert_all_called=True)
async def test_responses_request_and_response(app: App, respx_mock: MockRouter):
    """responses 格式：system 走 instructions，工具定义扁平，用量为 input/output_tokens"""
    from src.plugins.llm.providers import ResponsesProvider
    from src.plugins.llm.schemas import ToolParam

    route = respx_mock.post("https://api.example.com/responses").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test-model",
                "status": "completed",
                "output": [
                    {"type": "reasoning", "summary": [{"type": "summary_text", "text": "在想"}]},
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "你好呀"}],
                    },
                ],
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "output_tokens_details": {"reasoning_tokens": 3},
                    "input_tokens_details": {"cached_tokens": 2},
                },
            },
        )
    )

    tools = [ToolParam(name="get_weather", description="查询天气", parameters={"type": "object", "properties": {}})]
    provider = ResponsesProvider(make_config("responses"))
    completion = await provider.chat(make_messages(), tools)

    payload = json.loads(route.calls[0].request.content)
    # system 不在 input 里，而是提到顶层 instructions
    assert payload["instructions"] == "你是一个助手"
    assert payload["input"][0]["content"][0] == {"type": "input_text", "text": "你好"}
    # 工具定义是扁平结构，没有 function 嵌套
    assert payload["tools"][0]["name"] == "get_weather"
    assert "function" not in payload["tools"][0]

    assert completion.content == "你好呀"
    assert completion.reasoning == "在想"
    assert completion.finish_reason == "stop"
    assert completion.usage.input_tokens == 10
    assert completion.usage.reasoning_tokens == 3
    assert completion.usage.cache_read_tokens == 2


@respx.mock(assert_all_called=True)
async def test_responses_tool_call_and_result(app: App, respx_mock: MockRouter):
    """responses 格式：工具结果作为 function_call_output 回传"""
    from src.plugins.llm.providers import ResponsesProvider
    from src.plugins.llm.schemas import Message, ToolCall

    route = respx_mock.post("https://api.example.com/responses").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test-model",
                "status": "completed",
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "call_1",
                        "name": "get_weather",
                        "arguments": '{"city": "成都"}',
                    }
                ],
            },
        )
    )

    messages = [
        Message.user("天气"),
        Message.assistant(tool_calls=[ToolCall(id="call_0", name="get_weather", arguments={"city": "成都"})]),
        Message.tool("call_0", "晴"),
    ]
    provider = ResponsesProvider(make_config("responses"))
    completion = await provider.chat(messages)

    payload = json.loads(route.calls[0].request.content)
    assert payload["input"][-1] == {"type": "function_call_output", "call_id": "call_0", "output": "晴"}

    assert completion.tool_calls[0].id == "call_1"
    assert completion.tool_calls[0].arguments == {"city": "成都"}
    assert completion.finish_reason == "tool_calls"


def test_responses_output_items_round_trip(app: App):
    """Responses 工具回合应把原始 output items 作为顶层 input items 回传"""
    from src.plugins.llm.providers import ResponsesProvider
    from src.plugins.llm.schemas import Message

    output = [
        {
            "id": "rs_1",
            "type": "reasoning",
            "summary": [{"type": "summary_text", "text": "需要查询天气"}],
        },
        {
            "id": "fc_1",
            "type": "function_call",
            "call_id": "call_1",
            "name": "get_weather",
            "arguments": '{"city":"成都"}',
        },
    ]
    provider = ResponsesProvider(make_config("responses"))
    completion = provider.parse_response({"model": "test-model", "status": "completed", "output": output})

    payload = provider.build_payload([Message.user("天气"), completion.message, Message.tool("call_1", "晴")])

    assert payload["input"] == [
        {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "天气"}]},
        *output,
        {"type": "function_call_output", "call_id": "call_1", "output": "晴"},
    ]


@respx.mock(assert_all_called=True)
async def test_responses_stream(app: App, respx_mock: MockRouter):
    """responses 格式：按事件名分发，工具参数分片累积"""
    from src.plugins.llm.providers import ResponsesProvider
    from src.plugins.llm.schemas import Message

    chunks = [
        'event: response.created\ndata: {"response":{"model":"test-model"}}\n\n',
        'event: response.output_item.added\ndata: {"output_index":0,'
        '"item":{"id":"rs_1","type":"reasoning","summary":[]}}\n\n',
        'event: response.reasoning_summary_text.delta\ndata: {"delta":"想"}\n\n',
        'event: response.output_item.done\ndata: {"output_index":0,'
        '"item":{"id":"rs_1","type":"reasoning","summary":[{"type":"summary_text","text":"想"}],'
        '"encrypted_content":"encrypted"}}\n\n',
        'event: response.output_item.added\ndata: {"output_index":1,'
        '"item":{"id":"msg_1","type":"message","role":"assistant","content":[]}}\n\n',
        'event: response.output_text.delta\ndata: {"delta":"你"}\n\n',
        'event: response.output_text.delta\ndata: {"delta":"好"}\n\n',
        'event: response.output_item.done\ndata: {"output_index":1,'
        '"item":{"id":"msg_1","type":"message","role":"assistant",'
        '"content":[{"type":"output_text","text":"你好"}]}}\n\n',
        'event: response.output_item.added\ndata: {"output_index":2,"item":{"type":"function_call","id":"fc_1",'
        '"call_id":"call_1","name":"get_weather"}}\n\n',
        'event: response.function_call_arguments.delta\ndata: {"item_id":"fc_1","delta":"{\\"city\\":"}\n\n',
        'event: response.function_call_arguments.done\ndata: {"item_id":"fc_1",'
        '"arguments":"{\\"city\\": \\"成都\\"}"}\n\n',
        'event: response.output_item.done\ndata: {"output_index":2,"item":{"type":"function_call",'
        '"id":"fc_1","call_id":"call_1","name":"get_weather",'
        '"arguments":"{\\"city\\": \\"成都\\"}"}}\n\n',
        'event: response.completed\ndata: {"response":{"model":"test-model",'
        '"usage":{"input_tokens":3,"output_tokens":2}}}\n\n',
    ]
    respx_mock.post("https://api.example.com/responses").mock(return_value=httpx.Response(200, text="".join(chunks)))

    provider = ResponsesProvider(make_config("responses", stream=True))
    completion = await provider.chat(make_messages())

    assert completion.content == "你好"
    assert completion.reasoning == "想"
    assert completion.tool_calls[0].id == "call_1"
    assert completion.tool_calls[0].name == "get_weather"
    assert completion.tool_calls[0].arguments == {"city": "成都"}
    assert completion.usage.output_tokens == 2

    payload = provider.build_payload([Message.user("天气"), completion.message, Message.tool("call_1", "晴")])
    assert [item["type"] for item in payload["input"]] == [
        "message",
        "reasoning",
        "message",
        "function_call",
        "function_call_output",
    ]
    assert payload["input"][1]["encrypted_content"] == "encrypted"
    assert payload["input"][3]["arguments"] == '{"city": "成都"}'


# ----------------------------------------------------------- anthropic 格式


@respx.mock(assert_all_called=True)
async def test_anthropic_request_and_response(app: App, respx_mock: MockRouter):
    """anthropic 格式：x-api-key 认证，system 提到顶层，工具用 input_schema"""
    from src.plugins.llm.providers import AnthropicProvider
    from src.plugins.llm.schemas import ToolParam

    route = respx_mock.post("https://api.example.com/v1/messages").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "claude-opus-5",
                "stop_reason": "end_turn",
                "content": [
                    {"type": "thinking", "thinking": "在想"},
                    {"type": "text", "text": "你好呀"},
                ],
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "cache_read_input_tokens": 2,
                    "cache_creation_input_tokens": 1,
                },
            },
        )
    )

    tools = [ToolParam(name="get_weather", description="查询天气", parameters={"type": "object", "properties": {}})]
    provider = AnthropicProvider(make_config("anthropic"))
    completion = await provider.chat(make_messages(), tools)

    request = route.calls[0].request
    payload = json.loads(request.content)
    # Anthropic 用 x-api-key 而非 Bearer
    assert request.headers["x-api-key"] == "sk-test"
    assert request.headers["anthropic-version"] == "2023-06-01"
    assert payload["system"] == "你是一个助手"
    assert payload["messages"][0] == {"role": "user", "content": [{"type": "text", "text": "你好"}]}
    # max_tokens 是必填项
    assert payload["max_tokens"] > 0
    assert payload["tools"][0]["input_schema"] == {"type": "object", "properties": {}}

    assert completion.content == "你好呀"
    assert completion.reasoning == "在想"
    # stop_reason 已归一化
    assert completion.finish_reason == "stop"
    assert completion.usage.cache_read_tokens == 2
    assert completion.usage.cache_write_tokens == 1


@respx.mock(assert_all_called=True)
async def test_anthropic_tool_result_folds_into_user(app: App, respx_mock: MockRouter):
    """anthropic 格式：tool 角色不存在，工具结果折叠进 user 消息的 tool_result 块"""
    from src.plugins.llm.providers import AnthropicProvider
    from src.plugins.llm.schemas import Message, ToolCall

    route = respx_mock.post("https://api.example.com/v1/messages").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "claude-opus-5",
                "stop_reason": "tool_use",
                "content": [
                    {"type": "tool_use", "id": "toolu_1", "name": "get_weather", "input": {"city": "成都"}},
                ],
            },
        )
    )

    messages = [
        Message.user("天气"),
        Message.assistant(tool_calls=[ToolCall(id="toolu_0", name="get_weather", arguments={"city": "成都"})]),
        Message.tool("toolu_0", "晴"),
        Message.tool("toolu_x", "26 度"),
    ]
    provider = AnthropicProvider(make_config("anthropic"))
    completion = await provider.chat(messages)

    payload = json.loads(route.calls[0].request.content)
    # 两条工具结果被合并进同一条 user 消息，避免出现连续 user 消息
    assert payload["messages"][-1]["role"] == "user"
    assert [b["type"] for b in payload["messages"][-1]["content"]] == ["tool_result", "tool_result"]
    assert payload["messages"][1]["content"][0]["type"] == "tool_use"

    assert completion.tool_calls[0].id == "toolu_1"
    assert completion.tool_calls[0].arguments == {"city": "成都"}
    assert completion.finish_reason == "tool_calls"


def test_anthropic_thinking_blocks_round_trip(app: App):
    """Anthropic 工具回合应原样回传 thinking、signature 与 redacted_thinking"""
    from src.plugins.llm.providers import AnthropicProvider
    from src.plugins.llm.schemas import Message

    content = [
        {"type": "thinking", "thinking": "需要查询天气", "signature": "sig_1"},
        {"type": "redacted_thinking", "data": "encrypted"},
        {"type": "tool_use", "id": "toolu_1", "name": "get_weather", "input": {"city": "成都"}},
    ]
    provider = AnthropicProvider(make_config("anthropic"))
    completion = provider.parse_response(
        {
            "model": "claude-opus-5",
            "stop_reason": "tool_use",
            "content": content,
        }
    )

    payload = provider.build_payload(
        [Message.user("天气"), completion.message, Message.tool("toolu_1", "晴")]
    )

    assert payload["messages"][1] == {"role": "assistant", "content": content}


@respx.mock(assert_all_called=True)
async def test_anthropic_image_uses_base64_source(app: App, respx_mock: MockRouter):
    """anthropic 格式：图片用 source.base64，不带 data URI 前缀"""
    from src.plugins.llm.providers import AnthropicProvider
    from src.plugins.llm.schemas import ImageContent, Message

    route = respx_mock.post("https://api.example.com/v1/messages").mock(
        return_value=httpx.Response(
            200,
            json={"model": "claude-opus-5", "stop_reason": "end_turn", "content": [{"type": "text", "text": "好"}]},
        )
    )

    messages = [Message.user("这是什么", [ImageContent(data=b"fakeimage", mimetype="image/jpeg")])]
    provider = AnthropicProvider(make_config("anthropic"))
    await provider.chat(messages)

    payload = json.loads(route.calls[0].request.content)
    source = payload["messages"][0]["content"][0]["source"]
    assert source["type"] == "base64"
    assert source["media_type"] == "image/jpeg"
    assert not source["data"].startswith("data:")


@respx.mock(assert_all_called=True)
async def test_anthropic_stream(app: App, respx_mock: MockRouter):
    """anthropic 格式：内容块按 index 累积，工具入参是 partial_json 分片"""
    from src.plugins.llm.providers import AnthropicProvider
    from src.plugins.llm.schemas import Message

    chunks = [
        'event: message_start\ndata: {"type":"message_start","message":{"model":"claude-opus-5",'
        '"usage":{"input_tokens":10,"output_tokens":0}}}\n\n',
        'event: content_block_start\ndata: {"type":"content_block_start","index":0,'
        '"content_block":{"type":"thinking"}}\n\n',
        'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,'
        '"delta":{"type":"thinking_delta","thinking":"想"}}\n\n',
        'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,'
        '"delta":{"type":"signature_delta","signature":"sig_1"}}\n\n',
        'event: content_block_stop\ndata: {"type":"content_block_stop","index":0}\n\n',
        'event: content_block_start\ndata: {"type":"content_block_start","index":1,'
        '"content_block":{"type":"redacted_thinking","data":"encrypted"}}\n\n',
        'event: content_block_stop\ndata: {"type":"content_block_stop","index":1}\n\n',
        'event: content_block_start\ndata: {"type":"content_block_start","index":2,'
        '"content_block":{"type":"text","text":""}}\n\n',
        'event: content_block_delta\ndata: {"type":"content_block_delta","index":2,'
        '"delta":{"type":"text_delta","text":"你好"}}\n\n',
        'event: content_block_stop\ndata: {"type":"content_block_stop","index":2}\n\n',
        'event: content_block_start\ndata: {"type":"content_block_start","index":3,'
        '"content_block":{"type":"tool_use","id":"toolu_1","name":"get_weather"}}\n\n',
        'event: content_block_delta\ndata: {"type":"content_block_delta","index":3,'
        '"delta":{"type":"input_json_delta","partial_json":"{\\"city\\":"}}\n\n',
        'event: content_block_delta\ndata: {"type":"content_block_delta","index":3,'
        '"delta":{"type":"input_json_delta","partial_json":" \\"成都\\"}"}}\n\n',
        'event: content_block_stop\ndata: {"type":"content_block_stop","index":3}\n\n',
        'event: message_delta\ndata: {"type":"message_delta","delta":{"stop_reason":"tool_use"},'
        '"usage":{"output_tokens":7}}\n\n',
        'event: message_stop\ndata: {"type":"message_stop"}\n\n',
    ]
    respx_mock.post("https://api.example.com/v1/messages").mock(return_value=httpx.Response(200, text="".join(chunks)))

    provider = AnthropicProvider(make_config("anthropic", stream=True))
    completion = await provider.chat(make_messages())

    assert completion.content == "你好"
    assert completion.reasoning == "想"
    assert completion.tool_calls[0].name == "get_weather"
    assert completion.tool_calls[0].arguments == {"city": "成都"}
    assert completion.finish_reason == "tool_calls"
    assert completion.usage.input_tokens == 10
    assert completion.usage.output_tokens == 7

    payload = provider.build_payload([Message.user("天气"), completion.message, Message.tool("toolu_1", "晴")])
    assistant_content = payload["messages"][1]["content"]
    assert assistant_content[0] == {"type": "thinking", "thinking": "想", "signature": "sig_1"}
    assert assistant_content[1] == {"type": "redacted_thinking", "data": "encrypted"}


# ------------------------------------------------------------------ 其他


@respx.mock(assert_all_called=True)
async def test_error_response_raises(app: App, respx_mock: MockRouter):
    """错误响应转换成 ProviderError"""
    from src.plugins.llm.providers import ChatProvider, ProviderError

    respx_mock.post("https://api.example.com/chat/completions").mock(
        return_value=httpx.Response(401, json={"error": {"message": "无效的密钥"}})
    )

    provider = ChatProvider(make_config("chat"))
    with pytest.raises(ProviderError, match="无效的密钥"):
        await provider.chat(make_messages())


async def test_get_provider_unknown(app: App):
    """未知格式给出明确提示"""
    from src.plugins.llm.providers import ProviderError, get_provider

    with pytest.raises(ProviderError, match="不支持的 API 格式"):
        get_provider("gemini")


def test_endpoints(app: App):
    """三种格式的请求地址各不相同"""
    from src.plugins.llm.providers import AnthropicProvider, ChatProvider, ResponsesProvider

    assert ChatProvider(make_config("chat")).endpoint == "https://api.example.com/chat/completions"
    assert ResponsesProvider(make_config("responses")).endpoint == "https://api.example.com/responses"
    assert AnthropicProvider(make_config("anthropic")).endpoint == "https://api.example.com/v1/messages"
