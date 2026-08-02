"""测试 /llm 命令"""

import json

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
    return config


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

    respx_mock.post("https://api.example.com/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "你好呀"}}],
            },
        )
    )

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, Message("你好呀"), True)


@respx.mock(assert_all_called=True)
async def test_llm_with_thinking(app: App, respx_mock: MockRouter, mock_models, mocker):
    """开启推理内容展示时附带思考过程"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.handler import THINKING_SEPARATOR

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
        ctx.should_call_send(event, Message(f"在想{THINKING_SEPARATOR}你好呀"), True)


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
                },
            ),
            httpx.Response(
                200,
                json={
                    "model": "test-model",
                    "choices": [
                        {"finish_reason": "stop", "message": {"role": "assistant", "content": "成都晴，25 度"}}
                    ],
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
            ctx.should_call_send(event, Message("成都晴，25 度"), True)
    finally:
        # 清理注册的工具，避免影响其他测试
        registry._registry.pop("get_weather", None)

    # 第二轮请求里应包含工具执行结果
    second = respx_mock.calls[1].request
    payload = json.loads(second.content)
    assert payload["messages"][-1]["role"] == "tool"
    assert payload["messages"][-1]["tool_call_id"] == "call_1"
    assert payload["messages"][-1]["content"] == "晴，25 度"


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
            "支持的模型列表：\n- test-model（当前）\n输入 /llm [内容] --model [模型名] 单次指定模型\n"
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
        ctx.should_call_send(event, Message("**加粗**"), True)
