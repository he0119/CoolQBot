"""测试 /llm 命令"""

import asyncio
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

from tests.fake import fake_group_message_event_v11, fake_private_message_event_v11


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
    mocker.patch("src.plugins.llm.get_available_model_names", return_value=["test-model"])
    mocker.patch("src.plugins.llm.get_model_name", return_value="test-model")
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


def test_extract_context_reply_keeps_message_id(app: App, mocker):
    """续聊消息在 waiter 的事件上下文中保存消息 ID"""
    from src.plugins.llm import _extract_reply

    event = fake_group_message_event_v11(message=Message("继续聊"), message_id=42)
    get_message_id = mocker.patch("src.plugins.llm.get_message_id", return_value="42")

    message, message_id = _extract_reply(event)

    assert message == event.get_message()
    assert message_id == "42"
    get_message_id.assert_called_once_with(event)


async def test_context_reply_reacts_to_current_message(app: App, mocker):
    """多轮续聊把当前消息 ID 传给模型响应流程"""
    from src.plugins.llm import _handle_with_context

    class StopConversation(Exception):
        pass

    handler = mocker.Mock()
    handler.send = mocker.AsyncMock()
    first_completion = object()
    ask = mocker.patch(
        "src.plugins.llm._ask",
        side_effect=[first_completion, StopConversation],
    )
    mocker.patch(
        "nonebot_plugin_waiter.prompt",
        return_value=(Message("继续聊"), "42"),
    )

    with pytest.raises(StopConversation):
        await _handle_with_context(handler, "开始", None)

    assert ask.await_args_list == [
        call(handler, "开始", None),
        call(handler, "继续聊", None, message_id="42"),
    ]
    handler.send.assert_awaited_once_with(first_completion)


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


async def test_llm_denies_group_without_available_models(app: App, mocker):
    """全局存在模型时，未开放模型的群仍默认拒绝调用。"""
    from src.plugins.llm import llm_cmd
    from src.plugins.llm.config import ModelConfig, plugin_config

    mocker.patch.object(plugin_config, "models", [ModelConfig(name="test-model")])

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "本群未开放任何模型，请联系超级管理员配置", True, at_sender=True)
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
    tool_names = {tool["function"]["name"] for tool in json.loads(request.content)["tools"]}
    assert "web_fetch" in tool_names
    assert "web_search" not in tool_names


@respx.mock(assert_all_called=True)
async def test_llm_search_option_enables_web_search(app: App, respx_mock: MockRouter, mock_models):
    """-s 按次启用网页搜索，同时保留默认可用的网页读取工具。"""
    route = respx_mock.post("https://api.example.com/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "搜索结果"}}],
            },
        )
    )

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm -s 查询新消息"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message("搜索结果\n\n--- 5.1s  test-model  I:0 O:0 A:0 C:0"),
            True,
        )

    payload = json.loads(route.calls[0].request.content)
    tool_names = {tool["function"]["name"] for tool in payload["tools"]}
    assert {"web_search", "web_fetch"} <= tool_names


async def test_llm_group_mention_uses_default_chat_flow(app: App, mock_models, mocker):
    """群聊明确 @ 机器人时复用默认模型与标准问答流程。"""
    from src.plugins.llm import llm_mention

    handler = mocker.Mock()
    handler.send = mocker.AsyncMock()
    completion = object()
    create_handler = mocker.patch("src.plugins.llm._create_handler", return_value=handler)
    ask = mocker.patch("src.plugins.llm._ask", return_value=completion)
    async with app.test_matcher(llm_mention) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="123456")
        event = fake_group_message_event_v11(
            self_id=123456,
            message_id=42,
            message=Message("你好"),
            to_me=True,
        )

        ctx.receive_event(bot, event)

    create_handler.assert_awaited_once()
    assert create_handler.await_args.kwargs == {}
    ask.assert_awaited_once_with(handler, "你好", None, message_id="42")
    handler.send.assert_awaited_once_with(completion, reply_to="42")


async def test_create_handler_prefers_markdown_unless_render_is_explicit(app: App, mock_models, mocker):
    """全局 Markdown 偏好生效，但显式 -r 仍强制渲染图片。"""
    from src.plugins.llm import _create_handler
    from src.plugins.llm.config import plugin_config

    mocker.patch.object(plugin_config, "prefer_markdown", True)
    mocker.patch.object(plugin_config, "md_to_pic", False)
    user = mocker.Mock(session_id="QQClient_10000")

    handler = await _create_handler(user)
    assert handler.send_markdown is True
    assert handler.send_md_pic is False

    rendered_handler = await _create_handler(user, render=True)
    assert rendered_handler.send_markdown is False
    assert rendered_handler.send_md_pic is True

    search_handler = await _create_handler(user, search=True)
    assert search_handler.enable_web_search is True


async def test_llm_mention_requires_to_me_message(app: App, mock_models):
    """普通消息不会触发快捷对话。"""
    from src.plugins.llm import llm_mention

    async with app.test_matcher(llm_mention) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="123456")
        event = fake_group_message_event_v11(
            self_id=123456,
            message=Message("你好"),
            to_me=False,
        )

        ctx.receive_event(bot, event)
        ctx.should_not_pass_rule(llm_mention)


async def test_llm_command_ignores_private_messages(app: App, mock_models):
    """所有 /llm 子命令共享同一条非私聊规则。"""
    from src.plugins.llm import llm_cmd

    async with app.test_matcher(llm_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="123456")
        event = fake_private_message_event_v11(
            self_id=123456,
            message=Message("/llm model --list"),
            to_me=True,
        )

        ctx.receive_event(bot, event)
        ctx.should_not_pass_rule(llm_cmd)


async def test_llm_mention_ignores_private_messages(app: App, mock_models):
    """私聊默认具有 to_me 状态时也不能触发快捷对话。"""
    from src.plugins.llm import llm_mention

    async with app.test_matcher(llm_mention) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="123456")
        event = fake_private_message_event_v11(
            self_id=123456,
            message=Message("你好"),
            to_me=True,
        )

        ctx.receive_event(bot, event)
        ctx.should_not_pass_rule(llm_mention)


@pytest.mark.parametrize(
    ("scene_type", "expected"),
    [
        ("PRIVATE", False),
        ("GROUP", True),
        ("GUILD", True),
        ("CHANNEL_TEXT", True),
    ],
)
async def test_llm_rule_rejects_only_private_scenes(app: App, mocker, scene_type: str, expected: bool):
    """私聊不能复用群级配置，群聊、频道和子频道保持可用。"""
    from nonebot_plugin_uninfo import Scene, SceneType

    from src.plugins.llm.rules import is_non_private

    user = mocker.Mock()
    user.session.scene = Scene(id="scene", type=SceneType[scene_type])

    assert await is_non_private(user) is expected


async def test_llm_mention_ignores_commands(app: App, mock_models, mocker):
    """@机器人执行带非空前缀的命令时不再同时触发 LLM 对话。"""
    import nonebot

    from src.plugins.llm import llm_mention

    mocker.patch.object(nonebot.get_driver().config, "command_start", {"/", ""})
    async with app.test_matcher(llm_mention) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="123456")
        event = fake_group_message_event_v11(
            self_id=123456,
            message=Message("/llm -h"),
            to_me=True,
        )

        ctx.receive_event(bot, event)
        ctx.should_not_pass_rule(llm_mention)


async def test_llm_mention_allows_plain_text_with_empty_command_start(app: App, mock_models, mocker):
    """空命令前缀不应导致所有快捷对话都被过滤。"""
    import nonebot

    from src.plugins.llm import llm_mention

    mocker.patch.object(nonebot.get_driver().config, "command_start", {"/", ""})
    handler = mocker.Mock()
    handler.send = mocker.AsyncMock()
    create_handler = mocker.patch("src.plugins.llm._create_handler", return_value=handler)
    ask = mocker.patch("src.plugins.llm._ask", return_value=object())
    async with app.test_matcher(llm_mention) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="123456")
        event = fake_group_message_event_v11(
            self_id=123456,
            message=Message("你好"),
            to_me=True,
        )

        ctx.receive_event(bot, event)

    create_handler.assert_awaited_once()
    ask.assert_awaited_once()
    handler.send.assert_awaited_once()


async def test_llm_mention_can_be_disabled(app: App, mock_models, mocker):
    """关闭配置后不响应 @ 机器人消息。"""
    from src.plugins.llm import llm_mention
    from src.plugins.llm.config import plugin_config

    mocker.patch.object(plugin_config, "respond_to_mention", False)
    async with app.test_matcher(llm_mention) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="123456")
        event = fake_group_message_event_v11(
            self_id=123456,
            message=Message("你好"),
            to_me=True,
        )

        ctx.receive_event(bot, event)
        ctx.should_not_pass_rule(llm_mention)


async def test_llm_handler_logs_metadata_without_content(app: App, mock_models, mocker):
    """会话日志使用随机关联 ID 和长度，不记录输入输出正文。"""
    from src.plugins.llm.handler import LLMHandler
    from src.plugins.llm.schemas import Completion, Message

    mocker.patch(
        "src.plugins.llm.handler.chat",
        return_value=Completion(
            message=Message.assistant(content="private-output"),
            model="actual-model",
            finish_reason="stop",
        ),
    )
    logger_info = mocker.patch("src.plugins.llm.handler.logger.info")
    handler = LLMHandler("test-model", session_affinity="abcdef1234567890")

    await handler.ask("private-input")

    log_text = " ".join(str(item) for item in logger_info.call_args_list)
    assert "abcdef12" in log_text
    assert "test-model" in log_text
    assert "actual-model" in log_text
    assert "private-input" not in log_text
    assert "private-output" not in log_text


async def test_llm_rejects_unknown_model(app: App, mock_models):
    """单次指定未启用模型时给出明确提示"""
    from src.plugins.llm import llm_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm --model missing 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "本群未启用的模型：missing，可用：test-model", True, at_sender=True)
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


@pytest.mark.parametrize(
    ("count", "request_count", "tool_call_count", "message_id", "expected", "expected_reply"),
    [
        (1, 1, 2, None, "🔍 正在查询资料（模型请求 1 次，工具调用 2 个），请稍候……", True),
        (2, 3, 4, "42", "⏳ 查询仍在进行（模型请求 3 次，工具调用 4 个），请再稍候……", "42"),
    ],
)
async def test_tool_wait_notice_replies_to_trigger_message(
    app: App,
    mocker,
    count: int,
    request_count: int,
    tool_call_count: int,
    message_id: str | None,
    expected: str,
    expected_reply: str | bool,
):
    """工具等待提示回复触发消息，并区分首次与后续心跳。"""
    from src.plugins.llm import _send_tool_wait_notice

    message = mocker.Mock()
    message.send = mocker.AsyncMock()
    text = mocker.patch("src.plugins.llm.UniMessage.text", return_value=message)

    await _send_tool_wait_notice(count, request_count, tool_call_count, message_id=message_id)

    text.assert_called_once_with(expected)
    message.send.assert_awaited_once_with(reply_to=expected_reply)


async def test_tool_wait_notice_repeats_until_final_completion(app: App, mock_models, mocker):
    """首次工具调用启动一个心跳，并持续到工具后的最终模型回复完成。"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.handler import LLMHandler
    from src.plugins.llm.schemas import Completion, Message, ToolCall

    tool_completion = Completion(
        message=Message.assistant(tool_calls=[ToolCall(id="call_1", name="web_search", arguments={})]),
        finish_reason="tool_calls",
    )
    final_completion = Completion(message=Message.assistant(content="结果"), finish_reason="stop")
    first_notice_sent = asyncio.Event()
    second_request_started = asyncio.Event()
    second_notice_sent = asyncio.Event()
    keep_second_notice_pending = asyncio.Event()
    notices: list[tuple[int, int, int]] = []
    chat_count = 0

    async def fake_chat(*args, **kwargs):
        nonlocal chat_count
        chat_count += 1
        if chat_count == 1:
            return tool_completion
        second_request_started.set()
        await second_notice_sent.wait()
        return final_completion

    async def execute(calls, context):
        await first_notice_sent.wait()
        context.append(Message.tool(calls[0].id, "搜索结果"))

    async def notify(count: int, request_count: int, tool_call_count: int) -> None:
        notices.append((count, request_count, tool_call_count))
        if count == 1:
            first_notice_sent.set()
            await second_request_started.wait()
        else:
            second_notice_sent.set()
            await keep_second_notice_pending.wait()

    mocker.patch.object(plugin_config, "tool_notice_delay", 0)
    mocker.patch.object(plugin_config, "tool_notice_interval", 0.001)
    mocker.patch("src.plugins.llm.handler.chat", side_effect=fake_chat)
    mocker.patch("src.plugins.llm.handler.execute_tool_calls", side_effect=execute)

    completion = await LLMHandler("test-model").ask("查资料", on_tool_wait=notify)

    assert completion.content == "结果"
    assert notices == [(1, 1, 1), (2, 2, 1)]


async def test_tool_round_limit_generates_final_response_without_tools(app: App, mock_models, mocker):
    """达到工具轮数上限后基于已有结果生成无工具收尾回复。"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.handler import TOOL_ROUND_LIMIT_PROMPT, LLMHandler
    from src.plugins.llm.schemas import Completion, Message, ToolCall, Usage

    first_tool_completion = Completion(
        message=Message.assistant(tool_calls=[ToolCall(id="call_1", name="get_weather", arguments={})]),
        finish_reason="tool_calls",
        usage=Usage(input_tokens=1, output_tokens=2),
        model="first-model",
    )
    pending_tool_completion = Completion(
        message=Message.assistant(tool_calls=[ToolCall(id="call_2", name="web_search", arguments={})]),
        finish_reason="tool_calls",
        usage=Usage(input_tokens=3, output_tokens=4),
        model="second-model",
    )
    final_completion = Completion(
        message=Message.assistant(content="根据已有天气信息：晴。"),
        finish_reason="stop",
        usage=Usage(input_tokens=5, output_tokens=6),
        model="final-model",
    )
    mocker.patch.object(plugin_config, "max_tool_rounds", 1)
    chat = mocker.patch(
        "src.plugins.llm.handler.chat",
        side_effect=[first_tool_completion, pending_tool_completion, final_completion],
    )

    async def execute(calls, context):
        context.append(Message.tool(calls[0].id, "晴"))

    execute_calls = mocker.patch("src.plugins.llm.handler.execute_tool_calls", side_effect=execute)
    handler = LLMHandler("test-model", system_prompt="测试人设")

    completion = await handler.ask("天气")

    assert completion.content == "根据已有天气信息：晴。"
    assert completion.usage == Usage(input_tokens=9, output_tokens=12)
    assert completion.model == "final-model"
    assert [message.role for message in handler.context] == ["system", "user", "assistant", "tool", "assistant"]
    assert handler.context[-1] is completion.message
    execute_calls.assert_awaited_once()
    assert execute_calls.await_args.args[0] == first_tool_completion.tool_calls
    assert execute_calls.await_args.args[1] is handler.context
    assert chat.await_count == 3
    final_call = chat.await_args_list[-1]
    assert final_call.kwargs == {"session_affinity": handler.session_affinity, "enable_tools": False}
    assert final_call.args[1][:2] == [
        Message(role="system", content="测试人设"),
        Message(role="system", content=TOOL_ROUND_LIMIT_PROMPT),
    ]
    assert final_call.args[1][2:] == handler.context[1:-1]


async def test_tool_round_limit_rolls_back_when_final_response_still_calls_tools(app: App, mock_models, mocker):
    """无工具收尾仍返回工具调用时不保留不完整的上下文。"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.handler import LLMHandler
    from src.plugins.llm.providers import ProviderError
    from src.plugins.llm.schemas import Completion, Message, ToolCall

    tool_completion = Completion(
        message=Message.assistant(tool_calls=[ToolCall(id="call_1", name="get_weather", arguments={})]),
        finish_reason="tool_calls",
    )
    mocker.patch.object(plugin_config, "max_tool_rounds", 1)
    chat = mocker.patch(
        "src.plugins.llm.handler.chat",
        side_effect=[tool_completion, tool_completion, tool_completion],
    )

    async def execute(calls, context):
        context.append(Message.tool(calls[0].id, "晴"))

    mocker.patch("src.plugins.llm.handler.execute_tool_calls", side_effect=execute)
    handler = LLMHandler("test-model")
    original_context = list(handler.context)

    with pytest.raises(ProviderError, match="达到上限后仍未生成最终回复"):
        await handler.ask("天气")

    assert handler.context == original_context
    assert chat.await_args_list[-1].kwargs["enable_tools"] is False


async def test_tool_round_limit_rolls_back_when_final_request_fails(app: App, mock_models, mocker):
    """无工具收尾请求失败时回滚当前问题。"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.handler import LLMHandler
    from src.plugins.llm.providers import ProviderError
    from src.plugins.llm.schemas import Completion, Message, ToolCall

    tool_completion = Completion(
        message=Message.assistant(tool_calls=[ToolCall(id="call_1", name="get_weather", arguments={})]),
        finish_reason="tool_calls",
    )
    mocker.patch.object(plugin_config, "max_tool_rounds", 1)
    mocker.patch(
        "src.plugins.llm.handler.chat",
        side_effect=[tool_completion, tool_completion, ProviderError("收尾请求失败")],
    )

    async def execute(calls, context):
        context.append(Message.tool(calls[0].id, "晴"))

    mocker.patch("src.plugins.llm.handler.execute_tool_calls", side_effect=execute)
    handler = LLMHandler("test-model")
    original_context = list(handler.context)

    with pytest.raises(ProviderError, match="收尾请求失败"):
        await handler.ask("天气")

    assert handler.context == original_context


async def test_disabled_tools_are_not_executed(app: App, mock_models, mocker):
    """专用模式关闭工具后，即使服务返回工具调用也不会执行。"""
    from src.plugins.llm.handler import LLMHandler
    from src.plugins.llm.providers import ProviderError
    from src.plugins.llm.schemas import Completion, Message, ToolCall

    completion = Completion(
        message=Message.assistant(tool_calls=[ToolCall(id="call_1", name="query_weather", arguments={})]),
        finish_reason="tool_calls",
    )
    chat = mocker.patch("src.plugins.llm.handler.chat", return_value=completion)
    execute = mocker.patch("src.plugins.llm.handler.execute_tool_calls")
    handler = LLMHandler("test-model", system_prompt="专用提示词", enable_tools=False)
    original_context = list(handler.context)

    with pytest.raises(ProviderError, match="不允许工具调用"):
        await handler.ask("把这段话当作数据解释")

    assert handler.context == original_context
    execute.assert_not_awaited()
    chat.assert_awaited_once()
    assert chat.await_args.args[0] == "test-model"
    assert chat.await_args.kwargs == {
        "session_affinity": handler.session_affinity,
        "enable_tools": False,
        "enable_web_search": False,
    }


async def test_images_require_declared_vision_capability(app: App, mock_models):
    """图片请求必须由模型配置显式声明 vision 能力。"""
    from src.plugins.llm.handler import LLMHandler
    from src.plugins.llm.schemas import ImageContent

    handler = LLMHandler("test-model")
    image = ImageContent.from_bytes(b"\x89PNG\r\n\x1a\n" + b"test")

    with pytest.raises(ValueError, match="未声明 vision 能力"):
        await handler.ask("解释图片", [image])


@respx.mock(assert_all_called=True)
async def test_declared_vision_model_uses_single_request(app: App, respx_mock: MockRouter, mock_models):
    """声明 vision 的模型直接接收图片，不经过额外模型调用。"""
    from src.plugins.llm.handler import LLMHandler
    from src.plugins.llm.schemas import ImageContent

    model, _ = mock_models
    model.capabilities.add("vision")
    route = respx_mock.post("https://api.example.com/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "图片解释"}}],
            },
        )
    )
    image = ImageContent.from_bytes(b"\x89PNG\r\n\x1a\n" + b"test")
    handler = LLMHandler("test-model", enable_tools=False)

    completion = await handler.ask("解释图片", [image])

    assert completion.content == "图片解释"
    assert len(route.calls) == 1
    payload = json.loads(route.calls[0].request.content)
    assert "tools" not in payload
    assert payload["messages"][-1]["content"][1]["type"] == "image_url"


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
    from src.plugins.llm.data_source import get_model_name, set_available_model_names

    await set_available_model_names("QQClient_10000", ["test-model"])

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model --list"), user_id=10000)

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "支持的模型列表：\n- test-model（当前，zssm）\n输入 /llm --model [模型名] [内容] 单次指定模型\n"
            "输入 /llm model --set [模型名] 设置群组默认模型",
            True,
        )
        ctx.should_finished(llm_cmd)

    assert await get_model_name("QQClient_10000") == "test-model"


async def test_llm_model_list_denies_group_without_available_models(app: App, mocker):
    """普通用户不能查看尚未开放模型的群组列表。"""
    from src.plugins.llm import llm_cmd
    from src.plugins.llm.config import ModelConfig, plugin_config

    mocker.patch.object(plugin_config, "models", [ModelConfig(name="test-model")])

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model -l"), user_id=10000)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "本群未开放任何模型，请联系超级管理员配置", True)
        ctx.should_finished(llm_cmd)


@respx.mock(assert_all_called=True)
async def test_superuser_sets_group_available_models(app: App, respx_mock: MockRouter, mocker):
    """只有超级管理员能配置本群可用模型。"""
    from src.plugins.llm import llm_cmd
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import get_available_model_names

    mocker.patch.object(
        plugin_config,
        "models",
        [ModelConfig(name="test-model"), ModelConfig(name="other"), ModelConfig(name="hidden")],
    )

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model -l -a"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "全部模型列表：\n"
            "- test-model（未开放）\n"
            "- other（未开放）\n"
            "- hidden（未开放）\n"
            "输入 /llm --model [模型名] [内容] 单次指定模型\n"
            "输入 /llm model --set [模型名] 设置群组默认模型\n"
            "输入 /llm model --set-available [模型名...] 设置本群开放模型",
            True,
        )
        ctx.should_finished(llm_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/llm model --set-available test-model other"),
            user_id=10,
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已设置本群可用模型：test-model、other", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    assert await get_available_model_names("QQClient_10000") == ["test-model", "other"]

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model -l"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "支持的模型列表：\n"
            "- test-model（当前，zssm）\n"
            "- other\n"
            "输入 /llm --model [模型名] [内容] 单次指定模型\n"
            "输入 /llm model --set [模型名] 设置群组默认模型",
            True,
        )
        ctx.should_finished(llm_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model -l -a"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "全部模型列表：\n"
            "- test-model（已开放，当前，zssm）\n"
            "- other（已开放）\n"
            "- hidden（未开放）\n"
            "输入 /llm --model [模型名] [内容] 单次指定模型\n"
            "输入 /llm model --set [模型名] 设置群组默认模型\n"
            "输入 /llm model --set-available [模型名...] 设置本群开放模型",
            True,
        )
        ctx.should_finished(llm_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model -l -a"), user_id=10000)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "该参数仅超级管理员可用", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/llm model --set-available hidden"),
            user_id=10000,
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "该指令仅超级管理员可用", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    assert await get_available_model_names("QQClient_10000") == ["test-model", "other"]

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm --model hidden 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "本群未启用的模型：hidden，可用：test-model、other", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model --clear-available"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已清空本群可用模型", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    assert await get_available_model_names("QQClient_10000") == []


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("/llm model --clear-available", "该指令仅超级管理员可用"),
        ("/llm model --set-zssm test-model", "该指令仅管理员可用"),
        ("/llm model --clear-zssm", "该指令仅管理员可用"),
        ("/llm model --set-vision test-model", "该指令仅管理员可用"),
        ("/llm model --clear-vision", "该指令仅管理员可用"),
    ],
)
async def test_group_model_management_requires_permission(app: App, mocker, command: str, expected: str):
    """群组模型管理命令在执行数据操作前检查相应权限。"""
    from src.plugins.llm import llm_cmd
    from src.plugins.llm.config import ModelConfig, plugin_config

    mocker.patch.object(plugin_config, "models", [ModelConfig(name="test-model")])

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message(command), user_id=10000)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, expected, True, at_sender=True)
        ctx.should_finished(llm_cmd)


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("/llm model --set hidden", "本群未启用的模型：hidden，可用：default、text、vision"),
        ("/llm model --set-available missing", "未配置的模型：missing"),
        ("/llm model --set-zssm hidden", "本群未启用的模型：hidden"),
        ("/llm model --set-vision text", "视觉模型 text 未声明 vision 能力"),
    ],
)
async def test_group_model_management_reports_validation_errors(app: App, mocker, command: str, expected: str):
    """群组模型管理命令把数据源校验错误返回给管理员。"""
    from src.plugins.llm import llm_cmd
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names

    mocker.patch.object(
        plugin_config,
        "models",
        [
            ModelConfig(name="default"),
            ModelConfig(name="text"),
            ModelConfig(name="vision", capabilities={"vision"}),
            ModelConfig(name="hidden"),
        ],
    )
    await set_available_model_names("QQClient_10000", ["default", "text", "vision"])

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message(command), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, expected, True, at_sender=True)
        ctx.should_finished(llm_cmd)


async def test_admin_clears_group_zssm_models(app: App, mocker):
    """管理员可以恢复解释模型跟随默认值与视觉模型自动选择。"""
    from src.plugins.llm import llm_cmd
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import (
        get_zssm_model_name,
        get_zssm_vision_model_name,
        set_available_model_names,
        set_zssm_model_name,
        set_zssm_vision_model_name,
    )

    mocker.patch.object(
        plugin_config,
        "models",
        [
            ModelConfig(name="default"),
            ModelConfig(name="explain"),
            ModelConfig(name="vision", capabilities={"vision"}),
        ],
    )
    await set_available_model_names("QQClient_10000", ["default", "explain", "vision"])
    await set_zssm_model_name("QQClient_10000", "explain")
    await set_zssm_vision_model_name("QQClient_10000", "vision")

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model --clear-zssm"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "本群解释模型已改为跟随默认模型", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model --clear-vision"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "本群解释视觉模型已恢复自动选择", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    assert await get_zssm_model_name("QQClient_10000") == "default"
    assert await get_zssm_vision_model_name("QQClient_10000") == "vision"


async def test_superuser_sets_available_models_with_provider_paths(app: App, mocker):
    """模型名中的斜杠不会导致群级可用模型列表丢失。"""
    from src.plugins.llm import llm_cmd
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import get_available_model_names, set_tts_model

    names = [
        "deepseek-v4-flash",
        "deepseek-ai/DeepSeek-V4-Flash",
        "Qwen/Qwen3.6-35B-A3B",
    ]
    mocker.patch.object(plugin_config, "models", [ModelConfig(name=name) for name in names])
    await set_tts_model("QQClient_10000", "existing-voice")

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message(
                "/llm model --set-available deepseek-v4-flash deepseek-ai/DeepSeek-V4-Flash Qwen/Qwen3.6-35B-A3B"
            ),
            user_id=10,
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "已设置本群可用模型：deepseek-v4-flash、deepseek-ai/DeepSeek-V4-Flash、Qwen/Qwen3.6-35B-A3B",
            True,
            at_sender=True,
        )
        ctx.should_finished(llm_cmd)

    assert await get_available_model_names("QQClient_10000") == names


@respx.mock(assert_all_called=True)
async def test_admin_sets_group_zssm_models(app: App, respx_mock: MockRouter, mocker):
    """群管理员可分别设置本群解释模型和视觉模型。"""
    from src.plugins.llm import llm_cmd
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import get_zssm_model_name, get_zssm_vision_model_name

    mocker.patch.object(
        plugin_config,
        "models",
        [
            ModelConfig(name="test-model"),
            ModelConfig(name="explain"),
            ModelConfig(name="vision", capabilities={"vision"}),
        ],
    )
    from src.plugins.llm.data_source import set_available_model_names

    await set_available_model_names("QQClient_10000", ["test-model", "explain", "vision"])

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model --set-zssm explain"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已设置本群解释模型为：explain", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model --set-vision vision"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已设置本群解释视觉模型为：vision", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    assert await get_zssm_model_name("QQClient_10000") == "explain"
    assert await get_zssm_vision_model_name("QQClient_10000") == "vision"

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model -l"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "支持的模型列表：\n"
            "- test-model（当前）\n"
            "- explain（zssm）\n"
            "- vision（zssm 视觉）\n"
            "输入 /llm --model [模型名] [内容] 单次指定模型\n"
            "输入 /llm model --set [模型名] 设置群组默认模型",
            True,
        )
        ctx.should_finished(llm_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/llm model -l -c"),
            user_id=10,
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "支持的模型列表：\n"
            "- test-model（当前，能力：无）\n"
            "- explain（zssm，能力：无）\n"
            "- vision（zssm 视觉，能力：视觉）\n"
            "输入 /llm --model [模型名] [内容] 单次指定模型\n"
            "输入 /llm model --set [模型名] 设置群组默认模型",
            True,
        )
        ctx.should_finished(llm_cmd)


@respx.mock(assert_all_called=True)
async def test_llm_model_set_by_admin(app: App, respx_mock: MockRouter, mocker):
    """管理员可以设置群组默认模型"""
    from src.plugins.llm import llm_cmd
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import get_model_name, set_available_model_names

    mocker.patch.object(plugin_config, "models", [ModelConfig(name="test-model"), ModelConfig(name="other")])
    await set_available_model_names("QQClient_10000", ["test-model", "other"])

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
async def test_llm_model_set_by_normal_user(app: App, respx_mock: MockRouter, mocker):
    """普通用户不能修改群组默认模型"""
    from src.plugins.llm import llm_cmd
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import get_model_name, set_available_model_names

    mocker.patch.object(plugin_config, "models", [ModelConfig(name="test-model"), ModelConfig(name="other")])
    await set_available_model_names("QQClient_10000", ["test-model", "other"])

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


async def test_try_send_markdown_uses_native_style_on_supported_adapter(app: App, mocker):
    """支持的平台使用 UniSeg 的原生 Markdown 样式发送。"""
    from nonebot_plugin_alconna import SupportAdapter, UniMessage

    from src.plugins.llm.handler import try_send_markdown

    mocker.patch(
        "src.plugins.llm.handler.get_target",
        return_value=mocker.Mock(adapter=SupportAdapter.qq),
    )
    send = mocker.patch.object(UniMessage, "send", autospec=True)

    assert await try_send_markdown("**加粗**", reply_to="42") is True

    message = send.await_args.args[0]
    assert message[0].text == "**加粗**"
    assert message[0].extract_most_style() == "markdown"
    assert send.await_args.kwargs == {"reply_to": "42"}


async def test_try_send_markdown_skips_unsupported_adapter(app: App, mocker):
    """非 QQ 平台不尝试发送原生 Markdown，以便继续图片或文本回退。"""
    from nonebot_plugin_alconna import SupportAdapter, UniMessage

    from src.plugins.llm.handler import try_send_markdown

    mocker.patch(
        "src.plugins.llm.handler.get_target",
        return_value=mocker.Mock(adapter=SupportAdapter.discord),
    )
    send = mocker.patch.object(UniMessage, "send", autospec=True)

    assert await try_send_markdown("**加粗**") is False
    send.assert_not_awaited()


async def test_try_send_markdown_falls_back_after_send_error(app: App, mocker):
    """平台拒绝原生 Markdown 时返回失败，让调用方继续回退。"""
    from nonebot_plugin_alconna import SupportAdapter, UniMessage

    from src.plugins.llm.handler import try_send_markdown

    mocker.patch(
        "src.plugins.llm.handler.get_target",
        return_value=mocker.Mock(adapter=SupportAdapter.qq),
    )
    mocker.patch.object(UniMessage, "send", autospec=True, side_effect=RuntimeError("send failed"))

    assert await try_send_markdown("**加粗**") is False
