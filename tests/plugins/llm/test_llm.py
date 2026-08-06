"""测试 /chat 对话与 /llm 管理命令。"""

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
        provider="openai_chat_completions",
        base_url="https://api.example.com",
        api_key="sk-test",
    )
    mocker.patch.object(plugin_config, "models", [config])
    mocker.patch("src.plugins.llm.get_available_model_names", return_value=["test-model"])
    mocker.patch("src.plugins.llm.get_model_name", return_value="test-model")
    mocker.patch("src.plugins.llm.handler.perf_counter", side_effect=[10.0, 15.1])
    reaction = mocker.patch("src.plugins.llm.send_reaction")
    return config, reaction


def test_dialogue_command_is_separate_from_management(app: App):
    """管理关键字在普通与工具增强对话中仍作为普通正文。"""
    from src.plugins.llm import chat_command, llm_cmd

    result = chat_command.parse("/chat model tts quota")
    assert result.matched
    assert result.query("content").extract_plain_text() == "model tts quota"
    result = chat_command.parse("/chat -a model tts quota")
    assert result.matched
    assert result.query("agent.value") is True
    assert result.query("content").extract_plain_text() == "model tts quota"
    assert not llm_cmd.command().parse("/llm 你好").matched


@pytest.mark.parametrize("flag", ["-s", "--search"])
def test_removed_search_flags_are_plain_dialogue_content(app: App, flag: str):
    """已移除的搜索参数不再保留特殊语义。"""
    from src.plugins.llm import chat_command

    result = chat_command.parse(f"/chat {flag} 查询")

    assert result.matched
    assert result.query("content").extract_plain_text() == f"{flag} 查询"


@pytest.mark.parametrize(
    ("current_count", "replied_count", "expected"),
    [
        (1, 0, "随请求提供的 1 张图片均属于用户本次发送的消息。"),
        (1, 2, "随请求提供的前 1 张图片属于用户本次发送的消息，后 2 张属于用户正在回复或引用的消息。"),
    ],
)
def test_reply_context_describes_image_ownership(
    app: App,
    current_count: int,
    replied_count: int,
    expected: str,
):
    """图片归属说明覆盖当前消息独有及双方均有图片的情况。"""
    from src.plugins.llm import _format_reply_context

    result = _format_reply_context(
        "当前消息",
        "原消息",
        current_image_count=current_count,
        replied_image_count=replied_count,
    )

    assert result.endswith(expected)


def test_reply_context_defines_reply_target_without_negative_constraints(app: App):
    """自指问题使用明确的回复对象关系，不再加入诱发元分析的否定指令。"""
    from src.plugins.llm import _format_reply_context

    result = _format_reply_context(
        "我回复了什么？",
        "你好",
        current_image_count=0,
        replied_image_count=0,
    )

    assert result.startswith("【用户正在回复或引用的消息】\n你好")
    assert "【用户本次发送的消息】\n我回复了什么？" in result
    assert "不要" not in result
    assert "请" not in result


def test_session_affinity_is_per_conversation(app: App, mock_models):
    """每个 LLM 对话上下文使用独立的随机亲和键"""
    from src.plugins.llm.handler import LLMHandler

    first = LLMHandler("test-model")
    second = LLMHandler("test-model")

    assert UUID(first.session_affinity).version == 4
    assert UUID(second.session_affinity).version == 4
    assert first.session_affinity != second.session_affinity


def test_extract_context_reply_keeps_message_id(app: App, mocker):
    """续聊消息保留消息 ID 与下载图片所需的事件上下文。"""
    from src.plugins.llm import _extract_reply

    event = fake_group_message_event_v11(message=Message("继续聊"), message_id=42)
    bot = mocker.Mock()
    state = {}
    message = mocker.Mock()
    message_of = mocker.patch("src.plugins.llm.UniMessage.of", return_value=message)
    get_message_id = mocker.patch("src.plugins.llm.get_message_id", return_value="42")

    result = _extract_reply(event, bot, state)

    assert result == (message, "42", event, bot, state)
    message_of.assert_called_once_with(event.get_message(), bot=bot)
    get_message_id.assert_called_once_with(event)


async def test_context_reply_reacts_to_current_message(app: App, mocker):
    """多轮续聊把当前消息 ID 传给模型响应流程"""
    from src.plugins.llm import _handle_with_context, chat_cmd

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
        return_value=(
            mocker.Mock(extract_plain_text=mocker.Mock(return_value="继续聊"), get=mocker.Mock(return_value=[])),
            "42",
            mocker.Mock(),
            mocker.Mock(),
            {},
        ),
    )

    with pytest.raises(StopConversation):
        await _handle_with_context(handler, "开始", None)

    assert ask.await_args_list == [
        call(handler, "开始", None, finish_matcher=chat_cmd),
        call(handler, "继续聊", None, message_id="42", finish_matcher=chat_cmd),
    ]
    handler.send.assert_awaited_once_with(first_completion)


@pytest.mark.parametrize("reply_text", ["", "继续聊"])
async def test_context_reply_supports_images(app: App, mocker, reply_text: str):
    """多轮续聊保留仅图片和图文混合消息中的图片。"""
    from nonebot_plugin_alconna import Image, UniMessage

    from src.plugins.llm import _handle_with_context, chat_cmd

    class StopConversation(Exception):
        pass

    png = b"\x89PNG\r\n\x1a\n" + b"test"
    reply = UniMessage.text(reply_text) + Image(raw=png)
    reply_event = mocker.Mock()
    reply_bot = mocker.Mock()
    reply_state = {}
    handler = mocker.Mock()
    handler.send = mocker.AsyncMock()
    first_completion = object()
    ask = mocker.patch("src.plugins.llm._ask", side_effect=[first_completion, StopConversation])
    mocker.patch(
        "nonebot_plugin_waiter.prompt",
        return_value=(reply, "42", reply_event, reply_bot, reply_state),
    )
    image_fetch = mocker.patch("src.plugins.llm.image_fetch", return_value=png)

    with pytest.raises(StopConversation):
        await _handle_with_context(handler, "开始", None)

    assert ask.await_args_list[0] == call(handler, "开始", None, finish_matcher=chat_cmd)
    assert ask.await_args_list[1].args[:2] == (handler, reply_text)
    images = ask.await_args_list[1].args[2]
    assert len(images) == 1
    assert images[0].data == png
    assert ask.await_args_list[1].kwargs == {"message_id": "42", "finish_matcher": chat_cmd}
    image_fetch.assert_awaited_once_with(reply_event, reply_bot, reply_state, reply.get(Image)[0])
    handler.send.assert_awaited_once_with(first_completion)


@pytest.mark.asyncio
async def test_llm_not_configured(app: App):
    """未配置任何模型时的提示"""
    from src.plugins.llm.config import plugin_config

    plugin_config.models = []

    from src.plugins.llm import chat_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/chat 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "未配置任何模型，请先在 .env 中配置 LLM__MODELS",
            True,
        )
        ctx.should_finished(chat_cmd)


async def test_llm_denies_group_without_available_models(app: App, mocker):
    """全局存在模型时，未启用模型的群仍默认拒绝调用。"""
    from src.plugins.llm import chat_cmd
    from src.plugins.llm.config import ModelConfig, plugin_config

    mocker.patch.object(plugin_config, "models", [ModelConfig(name="test-model")])

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/chat 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "本群未启用任何模型，请联系超级管理员配置", True, at_sender=True)
        ctx.should_finished(chat_cmd)


@respx.mock(assert_all_called=True)
async def test_llm_chat(app: App, respx_mock: MockRouter, mock_models):
    """发送 /chat 你好得到模型回复。"""

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
        event = fake_group_message_event_v11(message=Message("/chat 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message(
                "你好呀\n\n---\n模型　deepseek-v4-flash  \n统计　5.1s · 输入 1,967 · 输出 410 · 缓存 1,152 · 共 2,377"
            ),
            True,
        )

    _, reaction = mock_models
    assert reaction.await_args_list == [
        call("thinking", message_id=None),
        call("done", message_id=None),
    ]

    request = route.calls[0].request
    assert UUID(request.headers["x-session-affinity"]).version == 4
    payload = json.loads(request.content)
    assert "tools" not in payload


@pytest.mark.parametrize("message", ["/chat -a 你好", "/agent 你好"])
@respx.mock(assert_all_called=True)
async def test_chat_agent_option_and_shortcut_enable_all_tools(
    app: App,
    respx_mock: MockRouter,
    mock_models,
    message: str,
):
    """-a 及其 /agent 快捷入口都发送包括网页搜索在内的全部工具。"""
    route = respx_mock.post("https://api.example.com/chat/completions").mock(
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
        event = fake_group_message_event_v11(message=Message(message))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message("你好呀\n\n---\n模型　test-model  \n统计　5.1s · 输入 0 · 输出 0 · 缓存 0 · 共 0"),
            True,
        )

    tool_names = {tool["function"]["name"] for tool in json.loads(route.calls[0].request.content)["tools"]}
    assert {"web_search", "web_fetch"} <= tool_names
    assert {
        "query_ff14_item_price",
        "query_ff14_fashion_report",
        "query_fflogs_character_ranking",
    } <= tool_names


@pytest.mark.parametrize(
    ("message", "enable_tools"),
    [("/chat 这句话什么意思？", False), ("/agent 这句话什么意思？", True)],
)
async def test_chat_and_agent_share_structured_reply_context(
    app: App,
    mock_models,
    mocker,
    message: str,
    enable_tools: bool,
):
    """/chat 与 /agent 都分别保留当前消息、被回复消息及图片归属。"""
    from nonebot.adapters.onebot.v11 import MessageSegment
    from nonebot.adapters.onebot.v11.event import Reply, Sender

    from src.plugins.llm import chat_cmd

    png = b"\x89PNG\r\n\x1a\n" + b"test"
    reply = Reply(
        time=1,
        message_type="group",
        message_id=99,
        real_id=99,
        sender=Sender(user_id=20, nickname="群友"),
        message=Message("测试协议啊") + MessageSegment.image(png),
    )
    handler = mocker.Mock()
    handler.send = mocker.AsyncMock()
    completion = object()
    create_handler = mocker.patch("src.plugins.llm._create_handler", return_value=handler)
    ask = mocker.patch("src.plugins.llm._ask", return_value=completion)
    fetch_image = mocker.patch("src.plugins.llm.image_fetch", return_value=png)

    async with app.test_matcher(chat_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="123456")
        event = fake_group_message_event_v11(
            self_id=123456,
            message_id=42,
            message=Message(message),
            reply=reply,
        )

        ctx.receive_event(bot, event)

    create_handler.assert_awaited_once_with(
        mocker.ANY,
        selected_model="",
        render=False,
        use_tts=False,
        enable_tools=enable_tools,
    )
    ask.assert_awaited_once()
    assert ask.await_args.args[0] is handler
    assert ask.await_args.args[1] == (
        "【用户正在回复或引用的消息】\n测试协议啊\n\n"
        "【用户本次发送的消息】\n这句话什么意思？\n\n"
        "【图片归属】\n随请求提供的 1 张图片均属于用户正在回复或引用的消息。"
    )
    images = ask.await_args.args[2]
    assert len(images) == 1
    assert images[0].data == png
    assert ask.await_args.kwargs == {"finish_matcher": chat_cmd}
    fetch_image.assert_awaited_once()
    handler.send.assert_awaited_once_with(completion)


async def test_chat_reports_reply_without_content(app: App, mock_models):
    """存在回复关系但平台未提供原消息时给出明确提示。"""
    from nonebot.adapters.onebot.v11.event import Reply, Sender

    from src.plugins.llm import chat_cmd

    reply = Reply(
        time=1,
        message_type="group",
        message_id=99,
        real_id=99,
        sender=Sender(user_id=20, nickname="群友"),
        message=Message(),
    )
    async with app.test_matcher(chat_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="123456")
        event = fake_group_message_event_v11(
            self_id=123456,
            message_id=42,
            message=Message("/chat 这句话什么意思？"),
            reply=reply,
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "上一条消息内容为空", True, at_sender=True)
        ctx.should_finished(chat_cmd)


@pytest.mark.parametrize(
    ("message", "enable_tools"),
    [("/chat", False), ("/agent", True)],
)
async def test_chat_reply_without_supplement_uses_replied_message_as_request(
    app: App,
    mock_models,
    mocker,
    message: str,
    enable_tools: bool,
):
    """只回复并发送命令时，直接把被回复内容作为实际请求。"""
    from nonebot.adapters.onebot.v11.event import Reply, Sender

    from src.plugins.llm import chat_cmd

    reply = Reply(
        time=1,
        message_type="group",
        message_id=99,
        real_id=99,
        sender=Sender(user_id=20, nickname="群友"),
        message=Message("测试协议啊"),
    )
    handler = mocker.Mock()
    handler.send = mocker.AsyncMock()
    completion = object()
    create_handler = mocker.patch("src.plugins.llm._create_handler", return_value=handler)
    ask = mocker.patch("src.plugins.llm._ask", return_value=completion)

    async with app.test_matcher(chat_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="123456")
        event = fake_group_message_event_v11(
            self_id=123456,
            message_id=42,
            message=Message(message),
            reply=reply,
        )

        ctx.receive_event(bot, event)

    create_handler.assert_awaited_once_with(
        mocker.ANY,
        selected_model="",
        render=False,
        use_tts=False,
        enable_tools=enable_tools,
    )
    ask.assert_awaited_once_with(handler, "测试协议啊", None, finish_matcher=chat_cmd)
    handler.send.assert_awaited_once_with(completion)


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
    assert create_handler.await_args.kwargs == {
        "selected_model": "",
        "render": False,
        "use_tts": False,
        "enable_tools": False,
    }
    ask.assert_awaited_once_with(handler, "你好", None, message_id="42")
    handler.send.assert_awaited_once_with(completion, reply_to="42")


async def test_llm_group_mention_supports_chat_options(app: App, mock_models, mocker):
    """@ 对话支持按次启用 agent 及常用对话选项。"""
    from src.plugins.llm import llm_mention

    handler = mocker.Mock()
    create_handler = mocker.patch("src.plugins.llm._create_handler", return_value=handler)
    handle_with_context = mocker.patch("src.plugins.llm._handle_with_context")
    async with app.test_matcher(llm_mention) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="123456")
        event = fake_group_message_event_v11(
            self_id=123456,
            message_id=42,
            message=Message("-a --model temporary -c -r -t 你好"),
            to_me=True,
        )

        ctx.receive_event(bot, event)

    create_handler.assert_awaited_once_with(
        mocker.ANY,
        selected_model="temporary",
        render=True,
        use_tts=True,
        enable_tools=True,
    )
    handle_with_context.assert_awaited_once_with(handler, "你好", None, message_id="42")


async def test_llm_group_mention_labels_replied_text(app: App, mock_models, mocker):
    """回复文字与当前问题使用明确标记分隔，避免模型误认为连续正文。"""
    from nonebot.adapters.onebot.v11.event import Reply, Sender

    from src.plugins.llm import llm_mention

    reply = Reply(
        time=1,
        message_type="group",
        message_id=99,
        real_id=99,
        sender=Sender(user_id=20, nickname="群友"),
        message=Message("测试协议啊"),
    )
    handler = mocker.Mock()
    handler.send = mocker.AsyncMock()
    completion = object()
    mocker.patch("src.plugins.llm._create_handler", return_value=handler)
    ask = mocker.patch("src.plugins.llm._ask", return_value=completion)

    async with app.test_matcher(llm_mention) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="123456")
        event = fake_group_message_event_v11(
            self_id=123456,
            message_id=42,
            message=Message("这句话什么意思？"),
            reply=reply,
            to_me=True,
        )

        ctx.receive_event(bot, event)

    ask.assert_awaited_once_with(
        handler,
        "【用户正在回复或引用的消息】\n测试协议啊\n\n【用户本次发送的消息】\n这句话什么意思？",
        None,
        message_id="42",
    )
    handler.send.assert_awaited_once_with(completion, reply_to="42")


async def test_llm_group_mention_reply_without_supplement_uses_replied_message(
    app: App,
    mock_models,
    mocker,
):
    """只回复并 @ 机器人时，被回复内容直接成为当前请求。"""
    from nonebot.adapters.onebot.v11.event import Reply, Sender

    from src.plugins.llm import llm_mention

    reply = Reply(
        time=1,
        message_type="group",
        message_id=99,
        real_id=99,
        sender=Sender(user_id=20, nickname="群友"),
        message=Message("测试协议啊"),
    )
    handler = mocker.Mock()
    handler.send = mocker.AsyncMock()
    completion = object()
    mocker.patch("src.plugins.llm._create_handler", return_value=handler)
    ask = mocker.patch("src.plugins.llm._ask", return_value=completion)

    async with app.test_matcher(llm_mention) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="123456")
        event = fake_group_message_event_v11(
            self_id=123456,
            message_id=42,
            message=Message(),
            reply=reply,
            to_me=True,
        )

        ctx.receive_event(bot, event)

    ask.assert_awaited_once_with(handler, "测试协议啊", None, message_id="42")
    handler.send.assert_awaited_once_with(completion, reply_to="42")


async def test_llm_group_mention_reply_only_image_uses_image_as_request(app: App, mock_models, mocker):
    """只回复图片并 @ 机器人时，直接把该图片作为当前请求。"""
    from nonebot.adapters.onebot.v11 import MessageSegment
    from nonebot.adapters.onebot.v11.event import Reply, Sender

    from src.plugins.llm import llm_mention

    png = b"\x89PNG\r\n\x1a\n" + b"test"
    reply = Reply(
        time=1,
        message_type="group",
        message_id=99,
        real_id=99,
        sender=Sender(user_id=20, nickname="群友"),
        message=Message(MessageSegment.image(png)),
    )
    handler = mocker.Mock()
    handler.send = mocker.AsyncMock()
    completion = object()
    mocker.patch("src.plugins.llm._create_handler", return_value=handler)
    ask = mocker.patch("src.plugins.llm._ask", return_value=completion)
    image_fetch = mocker.patch("src.plugins.llm.image_fetch", return_value=png)

    async with app.test_matcher(llm_mention) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="123456")
        event = fake_group_message_event_v11(
            self_id=123456,
            message_id=42,
            message=Message(),
            reply=reply,
            to_me=True,
        )

        ctx.receive_event(bot, event)

    ask.assert_awaited_once()
    assert ask.await_args.args[:2] == (handler, "")
    images = ask.await_args.args[2]
    assert len(images) == 1
    assert images[0].data == png
    assert ask.await_args.kwargs == {"message_id": "42"}
    image_fetch.assert_awaited_once()
    handler.send.assert_awaited_once_with(completion, reply_to="42")


async def test_llm_group_mention_merges_replied_image(app: App, mock_models, mocker):
    """@ 对话通过 Alconna 的回复扩展读取被回复消息中的图片。"""
    from nonebot.adapters.onebot.v11 import MessageSegment
    from nonebot.adapters.onebot.v11.event import Reply, Sender

    from src.plugins.llm import llm_mention

    png = b"\x89PNG\r\n\x1a\n" + b"test"
    reply = Reply(
        time=1,
        message_type="group",
        message_id=99,
        real_id=99,
        sender=Sender(user_id=20, nickname="群友"),
        message=Message(MessageSegment.image(png)),
    )
    handler = mocker.Mock()
    handler.send = mocker.AsyncMock()
    completion = object()
    mocker.patch("src.plugins.llm._create_handler", return_value=handler)
    ask = mocker.patch("src.plugins.llm._ask", return_value=completion)
    fetch_image = mocker.patch("src.plugins.llm.image_fetch", return_value=png)

    async with app.test_matcher(llm_mention) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="123456")
        event = fake_group_message_event_v11(
            self_id=123456,
            message_id=42,
            message=Message("请结合图片里的文字回答"),
            reply=reply,
            to_me=True,
        )

        ctx.receive_event(bot, event)

    ask.assert_awaited_once()
    assert ask.await_args.args[0] is handler
    assert ask.await_args.args[1] == (
        "【用户正在回复或引用的消息】\n（无文字）\n\n"
        "【用户本次发送的消息】\n请结合图片里的文字回答\n\n"
        "【图片归属】\n随请求提供的 1 张图片均属于用户正在回复或引用的消息。"
    )
    images = ask.await_args.args[2]
    assert len(images) == 1
    assert images[0].data == png
    assert ask.await_args.kwargs == {"message_id": "42"}
    fetch_image.assert_awaited_once()
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
    assert handler.enable_tools is False

    rendered_handler = await _create_handler(user, render=True)
    assert rendered_handler.send_markdown is False
    assert rendered_handler.send_md_pic is True

    agent_handler = await _create_handler(user, enable_tools=True)
    assert agent_handler.enable_tools is True


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


async def test_llm_mention_rule_ignores_events_without_message(app: App, mocker):
    """Alconna matcher 收到通知等非消息事件时不应读取消息正文。"""
    from src.plugins.llm.rules import should_handle_mention

    event = mocker.Mock()
    event.get_type.return_value = "notice"

    assert await should_handle_mention(mocker.Mock(), event, {}) is False
    event.get_plaintext.assert_not_called()


async def test_llm_mention_rule_checks_config_before_event(app: App, mocker):
    """关闭 @ 响应时直接短路，不再读取事件类型。"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.rules import should_handle_mention

    mocker.patch.object(plugin_config, "respond_to_mention", False)
    event = mocker.Mock()

    assert await should_handle_mention(mocker.Mock(), event, {}) is False
    event.get_type.assert_not_called()


@pytest.mark.parametrize("matcher_name", ["llm_cmd", "chat_cmd", "llm_mention"])
async def test_llm_entrypoints_reject_non_message_events_before_rules(app: App, mocker, matcher_name: str):
    """所有主 LLM 入口都在执行 Alconna 与业务规则前拒绝非消息事件。"""
    import src.plugins.llm as llm

    matcher = getattr(llm, matcher_name)
    event = mocker.Mock()
    event.get_type.return_value = "notice"

    assert await matcher.check_perm(mocker.Mock(), event) is False


@pytest.mark.parametrize(
    ("matcher_name", "message"),
    [("chat_cmd", "/chat 你好"), ("chat_cmd", "/agent 你好"), ("llm_cmd", "/llm model list")],
)
async def test_llm_commands_ignore_private_messages(app: App, mock_models, matcher_name: str, message: str):
    """对话与管理命令共享同一条非私聊规则。"""
    import src.plugins.llm as llm

    matcher = getattr(llm, matcher_name)
    async with app.test_matcher(matcher) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="123456")
        event = fake_private_message_event_v11(
            self_id=123456,
            message=Message(message),
            to_me=True,
        )

        ctx.receive_event(bot, event)
        ctx.should_not_pass_rule(matcher)


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

    session = mocker.Mock()
    session.scene = Scene(id="scene", type=SceneType[scene_type])

    assert await is_non_private(session) is expected


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
            message=Message("/chat -h"),
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
    assert "工具" in log_text
    assert "网页搜索" not in log_text
    assert "private-input" not in log_text
    assert "private-output" not in log_text


async def test_llm_rejects_unknown_model(app: App, mock_models):
    """单次指定未启用模型时给出明确提示"""
    from src.plugins.llm import chat_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/chat --model missing 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "本群未启用的模型：missing，可用：test-model", True, at_sender=True)
        ctx.should_finished(chat_cmd)


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
        event = fake_group_message_event_v11(message=Message("/chat 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message("> 在想\n\n你好呀\n\n---\n模型　test-model  \n统计　5.1s · 输入 0 · 输出 0 · 缓存 0 · 共 0"),
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
            event = fake_group_message_event_v11(message=Message("/agent 成都天气"))

            ctx.receive_event(bot, event)
            ctx.should_call_send(
                event,
                Message("成都晴，25 度\n\n---\n模型　test-model  \n统计　5.1s · 输入 30 · 输出 6 · 缓存 5 · 共 36"),
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
        (1, 1, 0, None, "⏳ 模型正在处理（模型请求 1/10 次），请稍候……", True),
        (2, 3, 4, "42", "⏳ 处理仍在进行（模型请求 3/10 次，工具调用 4 次），请再稍候……", "42"),
    ],
)
async def test_request_wait_notice_replies_to_trigger_message(
    app: App,
    mocker,
    count: int,
    request_count: int,
    tool_call_count: int,
    message_id: str | None,
    expected: str,
    expected_reply: str | bool,
):
    """请求等待提示回复触发消息，并区分首次与后续心跳。"""
    from src.plugins.llm import _send_request_wait_notice
    from src.plugins.llm.config import plugin_config

    mocker.patch.object(plugin_config, "max_requests", 10)
    message = mocker.Mock()
    message.send = mocker.AsyncMock()
    text = mocker.patch("src.plugins.llm.UniMessage.text", return_value=message)

    await _send_request_wait_notice(count, request_count, tool_call_count, message_id=message_id)

    text.assert_called_once_with(expected)
    message.send.assert_awaited_once_with(reply_to=expected_reply)


async def test_request_wait_notice_repeats_until_final_completion(app: App, mock_models, mocker):
    """等待提示从首次模型请求开始，并持续到工具后的最终回复完成。"""
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
            await first_notice_sent.wait()
            return tool_completion
        second_request_started.set()
        await second_notice_sent.wait()
        return final_completion

    async def execute(calls, context, **kwargs):
        context.append(Message.tool(calls[0].id, "搜索结果"))

    async def notify(count: int, request_count: int, tool_call_count: int) -> None:
        notices.append((count, request_count, tool_call_count))
        if count == 1:
            first_notice_sent.set()
        else:
            await second_request_started.wait()
            second_notice_sent.set()
            await keep_second_notice_pending.wait()

    mocker.patch.object(plugin_config, "request_notice_delay", 0)
    mocker.patch.object(plugin_config, "request_notice_interval", 0.001)
    mocker.patch("src.plugins.llm.handler.chat", side_effect=fake_chat)
    mocker.patch("src.plugins.llm.handler.execute_tool_calls", side_effect=execute)

    completion = await LLMHandler("test-model").ask("查资料", on_request_wait=notify)

    assert completion.content == "结果"
    assert notices == [(1, 1, 0), (2, 2, 1)]


async def test_request_wait_notice_is_cancelled_before_delay_for_fast_response(app: App, mock_models, mocker):
    """Agent 在提示延迟内直接完成时不发送等待提示。"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.handler import LLMHandler
    from src.plugins.llm.schemas import Completion, Message

    notify = mocker.AsyncMock()
    mocker.patch.object(plugin_config, "request_notice_delay", 60)
    mocker.patch(
        "src.plugins.llm.handler.chat",
        return_value=Completion(message=Message.assistant(content="结果"), finish_reason="stop"),
    )

    completion = await LLMHandler("test-model").ask("直接回答", on_request_wait=notify)

    assert completion.content == "结果"
    notify.assert_not_awaited()


async def test_request_wait_notice_is_cancelled_when_initial_request_fails(app: App, mock_models, mocker):
    """首次模型请求异常时也会取消并等待提示任务退出。"""
    from src.plugins.llm.handler import LLMHandler
    from src.plugins.llm.providers import ProviderError

    notice_started = asyncio.Event()
    notice_cancelled = asyncio.Event()

    async def send_notices(*args, **kwargs):
        notice_started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            notice_cancelled.set()
            raise

    async def fail_chat(*args, **kwargs):
        await notice_started.wait()
        raise ProviderError("请求失败")

    handler = LLMHandler("test-model")
    mocker.patch.object(handler, "_send_request_wait_notices", side_effect=send_notices)
    mocker.patch("src.plugins.llm.handler.chat", side_effect=fail_chat)

    with pytest.raises(ProviderError, match="请求失败"):
        await handler.ask("查资料", on_request_wait=mocker.AsyncMock())

    assert notice_cancelled.is_set()


async def test_request_limit_generates_final_response_with_tool_choice_none(app: App, mock_models, mocker):
    """最后一次请求保留缓存前缀，并以显式 none 生成收尾回复。"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.handler import (
        LAST_TOOL_REQUEST_PROMPT,
        REQUEST_BUDGET_PROMPT,
        REQUEST_LIMIT_PROMPT,
        LLMHandler,
    )
    from src.plugins.llm.schemas import Completion, Message, ToolCall, Usage

    first_tool_completion = Completion(
        message=Message.assistant(tool_calls=[ToolCall(id="call_1", name="get_weather", arguments={})]),
        finish_reason="tool_calls",
        usage=Usage(input_tokens=1, output_tokens=2),
        model="first-model",
    )
    final_completion = Completion(
        message=Message.assistant(content="根据已有天气信息：晴。"),
        finish_reason="stop",
        usage=Usage(input_tokens=5, output_tokens=6),
        model="final-model",
    )
    mocker.patch.object(plugin_config, "max_requests", 2)
    chat = mocker.patch(
        "src.plugins.llm.handler.chat",
        side_effect=[first_tool_completion, final_completion],
    )

    async def execute(calls, context, **kwargs):
        context.append(Message.tool(calls[0].id, "晴"))

    execute_calls = mocker.patch("src.plugins.llm.handler.execute_tool_calls", side_effect=execute)
    handler = LLMHandler("test-model", system_prompt="测试人设")

    completion = await handler.ask("天气")

    assert completion.content == "根据已有天气信息：晴。"
    assert completion.usage == Usage(input_tokens=6, output_tokens=8)
    assert completion.model == "final-model"
    assert [message.role for message in handler.context] == [
        "system",
        "system",
        "user",
        "assistant",
        "tool",
        "user",
        "assistant",
    ]
    assert handler.context[-1] is completion.message
    execute_calls.assert_awaited_once()
    assert execute_calls.await_args.args[0] == first_tool_completion.tool_calls
    assert execute_calls.await_args.args[1] is handler.context
    assert chat.await_count == 2
    initial_call = chat.await_args_list[0]
    assert initial_call.args[1] == handler.context[:3]
    assert initial_call.args[1][1] == Message(
        role="system",
        content=REQUEST_BUDGET_PROMPT.format(max_requests=2),
    )
    final_call = chat.await_args_list[-1]
    assert final_call.kwargs == {
        "session_affinity": handler.session_affinity,
        "enable_tools": True,
        "tool_choice": "none",
    }
    assert final_call.args[1] == handler.context[:-1]
    assert [message.role for message in final_call.args[1]] == [
        "system",
        "system",
        "user",
        "assistant",
        "tool",
        "user",
    ]
    assert final_call.args[1][-1] == Message.user(REQUEST_LIMIT_PROMPT)
    assert LAST_TOOL_REQUEST_PROMPT not in [message.content for message in handler.context]


async def test_request_limit_uses_completed_results_when_final_response_still_calls_tools(
    app: App,
    mock_models,
    mocker,
):
    """收尾仍返回结构化调用时保留已完成结果并生成确定性兜底。"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.handler import LLMHandler
    from src.plugins.llm.schemas import Completion, Message, ToolCall

    tool_completion = Completion(
        message=Message.assistant(tool_calls=[ToolCall(id="call_1", name="get_weather", arguments={})]),
        finish_reason="tool_calls",
    )
    mocker.patch.object(plugin_config, "max_requests", 2)
    chat = mocker.patch(
        "src.plugins.llm.handler.chat",
        side_effect=[tool_completion, tool_completion],
    )

    async def execute(calls, context, **kwargs):
        context.append(Message.tool(calls[0].id, "晴"))

    execute_calls = mocker.patch("src.plugins.llm.handler.execute_tool_calls", side_effect=execute)
    handler = LLMHandler("test-model")

    completion = await handler.ask("天气")

    assert "get_weather" in completion.content
    assert "晴" in completion.content
    assert not completion.tool_calls
    assert [message.role for message in handler.context] == ["system", "user", "assistant", "tool", "user", "assistant"]
    execute_calls.assert_awaited_once()
    assert chat.await_args_list[-1].kwargs == {
        "session_affinity": handler.session_affinity,
        "enable_tools": True,
        "tool_choice": "none",
    }


async def test_request_limit_uses_completed_results_when_final_request_fails(app: App, mock_models, mocker):
    """收尾请求失败时保留已完成结果并生成确定性兜底。"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.handler import LLMHandler
    from src.plugins.llm.providers import ProviderError
    from src.plugins.llm.schemas import Completion, Message, ToolCall

    tool_completion = Completion(
        message=Message.assistant(tool_calls=[ToolCall(id="call_1", name="get_weather", arguments={})]),
        finish_reason="tool_calls",
    )
    mocker.patch.object(plugin_config, "max_requests", 2)
    mocker.patch(
        "src.plugins.llm.handler.chat",
        side_effect=[tool_completion, ProviderError("收尾请求失败")],
    )

    async def execute(calls, context, **kwargs):
        context.append(Message.tool(calls[0].id, "晴"))

    mocker.patch("src.plugins.llm.handler.execute_tool_calls", side_effect=execute)
    handler = LLMHandler("test-model")

    completion = await handler.ask("天气")

    assert "get_weather" in completion.content
    assert "晴" in completion.content
    assert [message.role for message in handler.context] == ["system", "user", "assistant", "tool", "user", "assistant"]


async def test_request_limit_rejects_dsml_content_and_uses_completed_results(app: App, mock_models, mocker):
    """DeepSeek 把工具协议降级到正文时不得将 DSML 作为最终答案发送。"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.handler import LLMHandler
    from src.plugins.llm.schemas import Completion, Message, ToolCall

    tool_completion = Completion(
        message=Message.assistant(
            tool_calls=[ToolCall(id="call_1", name="query_fflogs_character_ranking", arguments={})],
        ),
        finish_reason="tool_calls",
    )
    dsml_completion = Completion(
        message=Message.assistant(
            content=(
                '<｜｜DSML｜｜tool_calls>\n<｜｜DSML｜｜invoke name="query_fflogs_character_ranking">\n'
                "</｜｜DSML｜｜invoke>\n</｜｜DSML｜｜tool_calls>"
            ),
        ),
        finish_reason="stop",
    )
    mocker.patch.object(plugin_config, "max_requests", 2)
    mocker.patch("src.plugins.llm.handler.chat", side_effect=[tool_completion, dsml_completion])

    async def execute(calls, context, **kwargs):
        context.append(Message.tool(calls[0].id, "角色排名：95"))

    mocker.patch("src.plugins.llm.handler.execute_tool_calls", side_effect=execute)

    completion = await LLMHandler("test-model").ask("查询排名")

    assert "角色排名：95" in completion.content
    assert "DSML" not in completion.content
    assert not completion.tool_calls


async def test_penultimate_request_warns_model_to_finish_tool_calls(app: App, mock_models, mocker):
    """最后一次允许工具的请求会提前要求模型集中完成剩余查询。"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.handler import LAST_TOOL_REQUEST_PROMPT, LLMHandler
    from src.plugins.llm.schemas import Completion, Message, ToolCall

    tool_completion = Completion(
        message=Message.assistant(tool_calls=[ToolCall(id="call_1", name="get_weather", arguments={})]),
        finish_reason="tool_calls",
    )
    final_completion = Completion(message=Message.assistant(content="天气是晴。"), finish_reason="stop")
    mocker.patch.object(plugin_config, "max_requests", 3)
    chat = mocker.patch("src.plugins.llm.handler.chat", side_effect=[tool_completion, final_completion])

    async def execute(calls, context, **kwargs):
        context.append(Message.tool(calls[0].id, "晴"))

    mocker.patch("src.plugins.llm.handler.execute_tool_calls", side_effect=execute)
    handler = LLMHandler("test-model")

    completion = await handler.ask("天气")

    assert completion.content == "天气是晴。"
    assert chat.await_count == 2
    second_context = chat.await_args_list[1].args[1]
    assert second_context == handler.context[:-1]
    assert second_context[-1] == Message.user(LAST_TOOL_REQUEST_PROMPT)
    assert LAST_TOOL_REQUEST_PROMPT in [message.content for message in handler.context]


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


async def test_vision_only_model_is_rejected_for_text_dialogue(app: App, mock_models, mocker):
    """仅视觉模型可以启用，但不能用于普通文本对话。"""
    from src.plugins.llm import chat_cmd
    from src.plugins.llm.config import ModelConfig, plugin_config

    text_model, _ = mock_models
    vision_model = ModelConfig(name="vision-only", capabilities={"vision"})
    mocker.patch.object(plugin_config, "models", [text_model, vision_model])
    mocker.patch(
        "src.plugins.llm.get_available_model_names",
        return_value=["test-model", "vision-only"],
    )

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/chat --model vision-only 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "模型 vision-only 未声明 text 能力，不能用于文本对话", True, at_sender=True)
        ctx.should_finished(chat_cmd)


async def test_missing_base_url_raises_config_error(app: App, mocker):
    """模型和全局地址都为空时在发起 HTTP 请求前给出明确错误。"""
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.handler import LLMHandler

    mocker.patch.object(plugin_config, "base_url", "")
    mocker.patch.object(plugin_config, "models", [ModelConfig(name="missing-url")])

    with pytest.raises(ValueError, match="模型 missing-url 未配置 base_url，且未设置 LLM__BASE_URL"):
        await LLMHandler("missing-url").ask("你好")


@respx.mock(assert_all_called=True)
async def test_llm_error_raises(app: App, respx_mock: MockRouter, mock_models):
    """API 返回错误时提示用户"""
    from src.plugins.llm import chat_cmd

    respx_mock.post("https://api.example.com/chat/completions").mock(
        return_value=httpx.Response(401, json={"error": {"message": "无效的密钥"}})
    )

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/chat 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "调用失败：无效的密钥", True, at_sender=True)
        ctx.should_finished(chat_cmd)

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
        event = fake_group_message_event_v11(message=Message("/llm model list"), user_id=10000)

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "本群已启用模型：\n- test-model（默认对话，zssm）\n\n"
            "对话：\n"
            "- 纯对话：/chat --model <模型名> <内容>\n"
            "- 工具增强：/agent --model <模型名> <内容>\n\n"
            "群组设置（管理员）：\n"
            "- 默认对话：/llm model set <模型名>\n"
            "- zssm：/llm model set-zssm <模型名>\n"
            "- zssm 跟随默认：/llm model clear-zssm\n"
            "- zssm 视觉：/llm model set-zssm-vision <模型名>\n"
            "- zssm 视觉自动选择：/llm model clear-zssm-vision",
            True,
        )
        ctx.should_finished(llm_cmd)

    assert await get_model_name("QQClient_10000") == "test-model"


async def test_llm_model_list_denies_group_without_available_models(app: App, mocker):
    """普通用户不能查看尚未启用模型的群组列表。"""
    from src.plugins.llm import llm_cmd
    from src.plugins.llm.config import ModelConfig, plugin_config

    mocker.patch.object(plugin_config, "models", [ModelConfig(name="test-model")])

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model list"), user_id=10000)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "本群未启用任何模型，请联系超级管理员配置", True)
        ctx.should_finished(llm_cmd)


@respx.mock(assert_all_called=True)
async def test_superuser_enables_and_disables_group_models(app: App, respx_mock: MockRouter, mocker):
    """超级管理员可为本群增量启用或禁用模型。"""
    from src.plugins.llm import chat_cmd, llm_cmd
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
        event = fake_group_message_event_v11(message=Message("/llm model list --all"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "全部模型：\n"
            "- test-model（未启用）\n"
            "- other（未启用）\n"
            "- hidden（未启用）\n\n"
            "对话：\n"
            "- 纯对话：/chat --model <模型名> <内容>\n"
            "- 工具增强：/agent --model <模型名> <内容>\n\n"
            "群组设置（管理员）：\n"
            "- 默认对话：/llm model set <模型名>\n"
            "- zssm：/llm model set-zssm <模型名>\n"
            "- zssm 跟随默认：/llm model clear-zssm\n"
            "- zssm 视觉：/llm model set-zssm-vision <模型名>\n"
            "- zssm 视觉自动选择：/llm model clear-zssm-vision\n\n"
            "模型管理（超级管理员）：\n"
            "- 启用：/llm model enable <模型名...>\n"
            "- 全部启用：/llm model enable --all\n"
            "- 禁用：/llm model disable <模型名...>\n"
            "- 全部禁用：/llm model disable --all",
            True,
        )
        ctx.should_finished(llm_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/llm model enable test-model"),
            user_id=10,
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已启用本群模型：test-model", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    assert await get_available_model_names("QQClient_10000") == ["test-model"]

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model enable other"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已启用本群模型：other", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    assert await get_available_model_names("QQClient_10000") == ["test-model", "other"]

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model list"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "本群已启用模型：\n"
            "- test-model（默认对话，zssm）\n"
            "- other\n\n"
            "对话：\n"
            "- 纯对话：/chat --model <模型名> <内容>\n"
            "- 工具增强：/agent --model <模型名> <内容>\n\n"
            "群组设置（管理员）：\n"
            "- 默认对话：/llm model set <模型名>\n"
            "- zssm：/llm model set-zssm <模型名>\n"
            "- zssm 跟随默认：/llm model clear-zssm\n"
            "- zssm 视觉：/llm model set-zssm-vision <模型名>\n"
            "- zssm 视觉自动选择：/llm model clear-zssm-vision",
            True,
        )
        ctx.should_finished(llm_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model list --all"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "全部模型：\n"
            "- test-model（已启用，默认对话，zssm）\n"
            "- other（已启用）\n"
            "- hidden（未启用）\n\n"
            "对话：\n"
            "- 纯对话：/chat --model <模型名> <内容>\n"
            "- 工具增强：/agent --model <模型名> <内容>\n\n"
            "群组设置（管理员）：\n"
            "- 默认对话：/llm model set <模型名>\n"
            "- zssm：/llm model set-zssm <模型名>\n"
            "- zssm 跟随默认：/llm model clear-zssm\n"
            "- zssm 视觉：/llm model set-zssm-vision <模型名>\n"
            "- zssm 视觉自动选择：/llm model clear-zssm-vision\n\n"
            "模型管理（超级管理员）：\n"
            "- 启用：/llm model enable <模型名...>\n"
            "- 全部启用：/llm model enable --all\n"
            "- 禁用：/llm model disable <模型名...>\n"
            "- 全部禁用：/llm model disable --all",
            True,
        )
        ctx.should_finished(llm_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model list --all"), user_id=10000)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "该参数仅超级管理员可用", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/llm model enable hidden"),
            user_id=10000,
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "该指令仅超级管理员可用", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    assert await get_available_model_names("QQClient_10000") == ["test-model", "other"]

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/chat --model hidden 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "本群未启用的模型：hidden，可用：test-model、other", True, at_sender=True)
        ctx.should_finished(chat_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model disable other"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已禁用本群模型：other", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    assert await get_available_model_names("QQClient_10000") == ["test-model"]

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model enable --all"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已启用本群全部模型", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    assert await get_available_model_names("QQClient_10000") == ["test-model", "other", "hidden"]

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model disable --all"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已禁用本群全部模型", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    assert await get_available_model_names("QQClient_10000") == []


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("/llm model enable test-model", "该指令仅超级管理员可用"),
        ("/llm model enable --all", "该指令仅超级管理员可用"),
        ("/llm model disable test-model", "该指令仅超级管理员可用"),
        ("/llm model disable --all", "该指令仅超级管理员可用"),
        ("/llm model set-zssm test-model", "该指令仅管理员可用"),
        ("/llm model clear-zssm", "该指令仅管理员可用"),
        ("/llm model set-zssm-vision test-model", "该指令仅管理员可用"),
        ("/llm model clear-zssm-vision", "该指令仅管理员可用"),
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
        ("/llm model set hidden", "本群未启用的模型：hidden，可用：default、text、vision"),
        ("/llm model enable", "请指定要启用的模型，或使用 --all 启用全部模型"),
        ("/llm model enable missing", "未配置的模型：missing"),
        ("/llm model enable default --all", "不能同时指定模型和 --all"),
        ("/llm model disable", "请指定要禁用的模型，或使用 --all 禁用全部模型"),
        ("/llm model disable missing", "未配置的模型：missing"),
        ("/llm model disable default --all", "不能同时指定模型和 --all"),
        ("/llm model set-zssm hidden", "本群未启用的模型：hidden"),
        ("/llm model set vision", "模型 vision 未声明 text 能力，不能用于文本对话"),
        ("/llm model set-zssm vision", "模型 vision 未声明 text 能力，不能用于文本解释"),
        ("/llm model set-zssm-vision text", "视觉模型 text 未声明 vision 能力"),
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
        event = fake_group_message_event_v11(message=Message("/llm model clear-zssm"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "本群解释模型已改为跟随默认模型", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model clear-zssm-vision"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "本群解释视觉模型已恢复自动选择", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    assert await get_zssm_model_name("QQClient_10000") == "default"
    assert await get_zssm_vision_model_name("QQClient_10000") == "vision"


async def test_superuser_enables_models_with_provider_paths(app: App, mocker):
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
            message=Message("/llm model enable deepseek-v4-flash deepseek-ai/DeepSeek-V4-Flash Qwen/Qwen3.6-35B-A3B"),
            user_id=10,
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "已启用本群模型：deepseek-v4-flash、deepseek-ai/DeepSeek-V4-Flash、Qwen/Qwen3.6-35B-A3B",
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
        event = fake_group_message_event_v11(message=Message("/llm model set-zssm explain"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已设置本群解释模型为：explain", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model set-zssm-vision vision"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已设置本群解释视觉模型为：vision", True, at_sender=True)
        ctx.should_finished(llm_cmd)

    assert await get_zssm_model_name("QQClient_10000") == "explain"
    assert await get_zssm_vision_model_name("QQClient_10000") == "vision"

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("/llm model list"), user_id=10)

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "本群已启用模型：\n"
            "- test-model（默认对话）\n"
            "- explain（zssm）\n"
            "- vision（zssm 视觉）\n\n"
            "对话：\n"
            "- 纯对话：/chat --model <模型名> <内容>\n"
            "- 工具增强：/agent --model <模型名> <内容>\n\n"
            "群组设置（管理员）：\n"
            "- 默认对话：/llm model set <模型名>\n"
            "- zssm：/llm model set-zssm <模型名>\n"
            "- zssm 跟随默认：/llm model clear-zssm\n"
            "- zssm 视觉：/llm model set-zssm-vision <模型名>\n"
            "- zssm 视觉自动选择：/llm model clear-zssm-vision",
            True,
        )
        ctx.should_finished(llm_cmd)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("/llm model list --capabilities"),
            user_id=10,
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "本群已启用模型：\n"
            "- test-model（默认对话，能力：文本）\n"
            "- explain（zssm，能力：文本）\n"
            "- vision（zssm 视觉，能力：视觉）\n\n"
            "对话：\n"
            "- 纯对话：/chat --model <模型名> <内容>\n"
            "- 工具增强：/agent --model <模型名> <内容>\n\n"
            "群组设置（管理员）：\n"
            "- 默认对话：/llm model set <模型名>\n"
            "- zssm：/llm model set-zssm <模型名>\n"
            "- zssm 跟随默认：/llm model clear-zssm\n"
            "- zssm 视觉：/llm model set-zssm-vision <模型名>\n"
            "- zssm 视觉自动选择：/llm model clear-zssm-vision",
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
        event = fake_group_message_event_v11(message=Message("/llm model set other"), user_id=10)

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
        event = fake_group_message_event_v11(message=Message("/llm model set other"), user_id=10000)

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
        event = fake_group_message_event_v11(message=Message("/chat -r 你好"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message("**加粗**\n\n---\n模型　test-model  \n统计　5.1s · 输入 0 · 输出 0 · 缓存 0 · 共 0"),
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
