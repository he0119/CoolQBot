"""测试 /llm 命令"""

import json
from unittest.mock import call
from uuid import UUID

import httpx
import pytest
import respx
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App
from respx import MockRouter

from tests.fake import fake_group_message_event_v11


@pytest.fixture
def mock_models(mocker):
    """配置一个测试用的模型列表，避免污染全局配置"""
    from src.plugins.llm.config import ModelConfig, plugin_config

    config = ModelConfig(
        name="test-model",
        provider="chat",
        base_url="https://api.example.com",
        api_key="sk-test",
    )
    mocker.patch.object(plugin_config, "models", [config])
    mocker.patch("src.plugins.llm.handler.perf_counter", side_effect=[10.0, 15.1])
    reaction = mocker.patch("src.plugins.llm.send_reaction")
    return config, reaction


def test_session_affinity_is_per_conversation(app: App, mock_models):
    """每个 LLM 对话上下文使用独立的随机亲和键"""
    from src.plugins.llm.handler import LLMHandler

    first = LLMHandler("test-model")
    second = LLMHandler("test-model")

    assert UUID(first.session_affinity).version == 4
    assert UUID(second.session_affinity).version == 4
    assert first.session_affinity != second.session_affinity


@pytest.mark.asyncio
async def test_llm_not_configured(app: App):
    """未配置任何模型时的提示"""
    from src.plugins.llm.config import plugin_config

    plugin_config.models = []

    from src.plugins.llm import llm_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "未配置任何模型，请先在 .env 中配置 LLM__MODELS",
            True,
        )
        ctx.should_finished(llm_cmd)


@respx.mock(assert_all_called=True)
async def test_llm_chat(app: App, respx_mock: MockRouter, mock_models):
    """发送 /llm 你好 得到模型回复"""

    route = respx_mock.post("https://api.example.com/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "deepseek-v4-flash",
                "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "你好呀"}}],
                "usage": {
                    "prompt_tokens": 1967,
                    "completion_tokens": 410,
                    "prompt_tokens_details": {"cached_tokens": 1152},
                },
            },
        )
    )

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message("你好呀\n\n--- 5.1s  deepseek-v4-flash  I:1967 O:410 A:2377 C:1152"),
            True,
        )

    _, reaction = mock_models
    assert reaction.await_args_list == [
        call("thinking", message_id=None),
        call("done", message_id=None),
    ]

    request = route.calls[0].request
    assert UUID(request.headers["x-session-affinity"]).version == 4


async def test_llm_rejects_unknown_model(app: App, mock_models):
    """单次指定未启用模型时给出明确提示"""
    from src.plugins.llm import llm_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm --model missing 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "未启用的模型：missing，可用：test-model", True, at_sender=True)
        ctx.should_finished(llm_cmd)


@respx.mock(assert_all_called=True)
async def test_llm_with_thinking(app: App, respx_mock: MockRouter, mock_models, mocker):
    """开启推理内容展示时附带思考过程"""
    from src.plugins.llm.config import plugin_config

    mocker.patch.object(plugin_config, "send_thinking", True)

    respx_mock.post("https://api.example.com/chat/completions").mock(
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
            },
        )
    )

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message("> 在想\n\n你好呀\n\n--- 5.1s  test-model  I:0 O:0 A:0 C:0"),
            True,
        )


@respx.mock(assert_all_called=True)
async def test_llm_with_tool(app: App, respx_mock: MockRouter, mock_models):
    """模型请求工具调用时自动执行并把结果交回模型"""
    from src.plugins.llm.tools import registry

    @registry.register("get_weather", "查询天气")
    async def get_weather(city: str) -> str:
        """查询天气

        Args:
            city: 城市名
        """
        return "晴，25 度"

    # 第一轮返回工具调用，第二轮返回最终答复
    respx_mock.post("https://api.example.com/chat/completions").mock(
        side_effect=[
            httpx.Response(
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
                                        "function": {
                                            "name": "get_weather",
                                            "arguments": '{"city": "成都"}',
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 1,
                        "prompt_tokens_details": {"cached_tokens": 3},
                    },
                },
            ),
            httpx.Response(
                200,
                json={
                    "model": "test-model",
                    "choices": [
                        {"finish_reason": "stop", "message": {"role": "assistant", "content": "成都晴，25 度"}}
                    ],
                    "usage": {
                        "prompt_tokens": 20,
                        "completion_tokens": 5,
                        "prompt_tokens_details": {"cached_tokens": 2},
                    },
                },
            ),
        ]
    )

    try:
        async with app.test_matcher() as ctx:
            adapter = get_adapter(Adapter)
            bot = ctx.create_bot(base=Bot, adapter=adapter)
            event = fake_group_message_event_v11(message=Message("/llm 成都天气"))

            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event,
                Message("成都晴，25 度\n\n--- 5.1s  test-model  I:30 O:6 A:36 C:5"),
                True,
            )
    finally:
        # 清理注册的工具，避免影响其他测试
        registry._registry.pop("get_weather", None)

    # 第二轮请求里应包含工具执行结果
    second = respx_mock.calls[1].request
    payload = json.loads(second.content)
    assert payload["messages"][-1]["role"] == "tool"
    assert payload["messages"][-1]["tool_call_id"] == "call_1"
    assert payload["messages"][-1]["content"] == "晴，25 度"
    affinities = {call.request.headers["x-session-affinity"] for call in respx_mock.calls}
    assert len(affinities) == 1
    assert UUID(affinities.pop()).version == 4


async def test_tool_round_limit_rolls_back_current_question(app: App, mock_models, mocker):
    """工具调用超过轮数上限时不保留不完整的上下文"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.handler import LLMHandler
    from src.plugins.llm.providers import ProviderError
    from src.plugins.llm.schemas import Completion, Message, ToolCall

    tool_completion = Completion(
        message=Message.assistant(tool_calls=[ToolCall(id="call_1", name="get_weather", arguments={})]),
        finish_reason="tool_calls",
    )
    mocker.patch.object(plugin_config, "max_tool_rounds", 1)
    mocker.patch("src.plugins.llm.handler.chat", side_effect=[tool_completion, tool_completion])

    async def execute(calls, context):
        context.append(Message.tool(calls[0].id, "晴"))

    mocker.patch("src.plugins.llm.handler.execute_tool_calls", side_effect=execute)
    handler = LLMHandler("test-model")
    original_context = list(handler.context)

    with pytest.raises(ProviderError, match="工具调用超过上限"):
        await handler.ask("天气")

    assert handler.context == original_context


@respx.mock(assert_all_called=True)
async def test_llm_error_raises(app: App, respx_mock: MockRouter, mock_models):
    """API 返回错误时提示用户"""
    from src.plugins.llm import llm_cmd

    respx_mock.post("https://api.example.com/chat/completions").mock(
        return_value=httpx.Response(401, json={"error": {"message": "无效的密钥"}})
    )

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "调用失败：无效的密钥", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    _, reaction = mock_models
    assert reaction.await_args_list == [
        call("thinking", message_id=None),
        call("fail", message_id=None),
    ]


@respx.mock(assert_all_called=True)
async def test_llm_model_list_and_set(app: App, respx_mock: MockRouter, mock_models):
    """模型列表与群组默认模型设置"""
    from src.plugins.llm import llm_cmd
    from src.plugins.llm.data_source import get_model_name

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model --list"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "支持的模型列表：\n- test-model（当前）\n输入 /llm --model [模型名] [内容] 单次指定模型\n"
            "输入 /llm model --set [模型名] 设置群组默认模型",
            True,
        )
        ctx.should_finished(llm_cmd)

    assert await get_model_name("QQClient_10000") == "test-model"


@respx.mock(assert_all_called=True)
async def test_llm_model_set_by_admin(app: App, respx_mock: MockRouter, mock_models, mocker):
    """管理员可以设置群组默认模型"""
    from src.plugins.llm import llm_cmd
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import get_model_name

    mocker.patch.object(plugin_config, "models", [ModelConfig(name="test-model"), ModelConfig(name="other")])

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        # user_id=10 是超级用户
        event = fake_group_message_event_v11(message=Message("/llm model --set other"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已设置群组默认模型为：other", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    assert await get_model_name("QQClient_10000") == "other"


@respx.mock(assert_all_called=True)
async def test_llm_model_set_by_normal_user(app: App, respx_mock: MockRouter, mock_models, mocker):
    """普通用户不能修改群组默认模型"""
    from src.plugins.llm import llm_cmd
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import get_model_name

    mocker.patch.object(plugin_config, "models", [ModelConfig(name="test-model"), ModelConfig(name="other")])

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        # user_id=10000 是普通用户
        event = fake_group_message_event_v11(message=Message("/llm model --set other"), user_id=10000)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "该指令仅管理员可用", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    # 设置未生效，仍是第一个模型
    assert await get_model_name("QQClient_10000") == "test-model"


@respx.mock(assert_all_called=True)
async def test_llm_send_md_pic_fallback(app: App, respx_mock: MockRouter, mock_models, mocker):
    """Markdown 渲染失败时退回文字回复"""

    # 直接让渲染函数失败，模拟 htmlrender 不可用
    mocker.patch("src.plugins.llm.handler.try_render_markdown", return_value=None)

    respx_mock.post("https://api.example.com/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "**加粗**"}}],
            },
        )
    )

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        # -r 要求渲染图片，但渲染失败时应退回文字
        event = fake_group_message_event_v11(message=Message("/llm -r 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message("**加粗**\n\n--- 5.1s  test-model  I:0 O:0 A:0 C:0"),
            True,
        )
