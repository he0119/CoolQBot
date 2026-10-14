"""测试内置 --shortcut 选项

该选项仅超级管理员可用，用于把某条对话命令固化成快捷命令。
"""

import contextlib
import json

import httpx
import pytest
import respx
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App
from respx import MockRouter

from tests.fake import fake_group_message_event_v11

REPLY = "你好呀\n\n---\n模型　test-model  \n统计　5.1s · 输入 0 · 输出 0 · 缓存 0 · 共 0"


@pytest.fixture
def model_env(mocker):
    """配置一个测试模型。"""
    from src.plugins.llm.config import ModelConfig, plugin_config

    config = ModelConfig(
        name="test-model",
        provider="openai_chat_completions",
        base_url="https://api.example.com",
        api_key="sk-test",
    )
    mocker.patch.object(plugin_config, "models", [config])
    mocker.patch("src.plugins.llm.get_available_model_names", return_value=["test-model"])
    mocker.patch("src.plugins.llm.get_model_name", return_value="test-model")
    mocker.patch("src.plugins.llm.handler.perf_counter", side_effect=[10.0, 15.1])
    mocker.patch("src.plugins.llm.send_reaction")
    return config


@pytest.fixture
def shortcut_state():
    """打开命令解析缓存（测试环境默认关闭），并在用例结束后还原注册状态。"""
    from arclet.alconna import command_manager

    from src.plugins.llm import chat_cmd

    command = chat_cmd.command()
    disabled = set(command.namespace_config.disable_builtin_options)
    message_cache = command.namespace_config.enable_message_cache
    command.namespace_config.enable_message_cache = True
    yield command
    command.namespace_config.enable_message_cache = message_cache
    command.namespace_config.disable_builtin_options.clear()
    command.namespace_config.disable_builtin_options.update(disabled)
    with contextlib.suppress(Exception):
        command.shortcut("/ds", delete=True)
    command_manager.clear_result(command)


def _mock_completion(respx_mock: MockRouter):
    return respx_mock.post("https://api.example.com/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "你好呀"}}],
            },
        )
    )


@respx.mock(assert_all_called=True)
async def test_superuser_registers_shortcut_from_recent_command(
    app: App,
    respx_mock: MockRouter,
    model_env,
    shortcut_state,
):
    """超级管理员用最近一次命令把 /chat --model X 固化成 /ds，之后 /ds 默认使用该模型。"""
    route = _mock_completion(respx_mock)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/chat --model test-model"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "你想问什么呢？输入 /chat -h 查看用法", True, at_sender=True)

        event = fake_group_message_event_v11(message=Message("/chat --shortcut /ds _"), message_id=2)
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, 'Alconna::chat 的快捷指令: "/ds" 添加成功', True)

        event = fake_group_message_event_v11(message=Message("/ds 你好"), message_id=3)
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, Message(REPLY), True)

    payload = json.loads(route.calls[0].request.content)
    assert payload["model"] == "test-model"
    assert payload["messages"][-1]["content"] == "你好"


@respx.mock(assert_all_called=True)
async def test_normal_user_cannot_use_shortcut_option(
    app: App,
    respx_mock: MockRouter,
    model_env,
    shortcut_state,
):
    """普通用户的 --shortcut 只是普通正文，不会注册快捷命令。"""
    route = _mock_completion(respx_mock)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(
            message=Message("/chat --shortcut /ds _"),
            user_id=10000,
        )
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, Message(REPLY), True)

    assert json.loads(route.calls[0].request.content)["messages"][-1]["content"] == "--shortcut /ds _"
    assert "/ds" not in shortcut_state.get_shortcuts()
