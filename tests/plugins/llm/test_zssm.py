"""测试 LLM 内置的“这是什么”解释模式。"""

import json
from unittest.mock import call

import httpx
import pymupdf
import pytest
import respx
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
from nonebot.adapters.onebot.v11.event import Reply as OneBotReply
from nonebot.adapters.onebot.v11.event import Sender
from nonebug import App
from respx import MockRouter

from tests.fake import fake_group_message_event_v11, fake_private_message_event_v11


@pytest.fixture
async def zssm_model(app: App, mocker):
    """配置解释模式测试模型。"""
    from src.plugins.llm.config import ModelConfig, plugin_config

    model = ModelConfig(
        name="test-model",
        provider="openai_chat_completions",
        base_url="https://api.example.com",
        api_key="sk-test",
    )
    mocker.patch.object(plugin_config, "models", [model])
    from src.plugins.llm.data_source import set_available_model_names

    await set_available_model_names("QQClient_10000", ["test-model"])
    mocker.patch("src.plugins.llm.handler.perf_counter", side_effect=[10.0, 15.1])
    reaction = mocker.patch("src.plugins.llm.plugins.zssm.send_reaction")
    return model, reaction


def test_zssm_has_help_metadata(app: App):
    """帮助信息使用插件描述，不显示 Alconna 的 Unknown 占位符。"""
    from src.plugins.llm.plugins.zssm import zssm_cmd

    command = zssm_cmd.command()
    assert command.meta.description == "使用大模型解释回复或输入的文字、图片、网页与 PDF"
    assert command.meta.example == (
        "回复一条消息并发送 zssm，可用 --model 临时指定模型、-r 渲染图片、-a 启用联网工具，并在后面补充关注点"
    )
    help_text = command.get_help()
    assert command.meta.description in help_text
    assert "Unknown" not in help_text


async def test_zssm_rejects_non_message_events_before_rules(app: App, mocker):
    """zssm 与其他 LLM 入口一样先拒绝非消息事件。"""
    from src.plugins.llm.plugins.zssm import zssm_cmd

    event = mocker.Mock()
    event.get_type.return_value = "notice"

    assert await zssm_cmd.check_perm(mocker.Mock(), event) is False


async def test_zssm_ignores_private_messages(app: App):
    """解释模式与主 LLM 入口一样不允许在私聊中使用。"""
    from src.plugins.llm.plugins.zssm import zssm_cmd

    async with app.test_matcher(zssm_cmd) as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter, self_id="123456")
        event = fake_private_message_event_v11(
            self_id=123456,
            message=Message("zssm Python GIL"),
            to_me=True,
        )

        ctx.receive_event(bot, event)
        ctx.should_not_pass_rule(zssm_cmd)


async def test_zssm_not_configured(app: App, mocker):
    """未配置模型时在读取群组默认值前给出明确提示。"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.plugins.zssm import zssm_cmd

    mocker.patch.object(plugin_config, "models", [])

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("zssm Python GIL"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message(MessageSegment.reply(1)) + "未配置任何模型，请先在 .env 中配置 LLM__MODELS",
            True,
        )
        ctx.should_finished(zssm_cmd)


async def test_zssm_denies_group_without_available_models(app: App, mocker):
    """全局存在模型时，未启用模型的群仍不能使用解释模式。"""
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.plugins.zssm import zssm_cmd

    mocker.patch.object(plugin_config, "models", [ModelConfig(name="test-model")])

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("zssm Python GIL"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message(MessageSegment.reply(1)) + "本群未启用任何模型，请联系超级管理员配置",
            True,
        )
        ctx.should_finished(zssm_cmd)


@respx.mock(assert_all_called=True)
async def test_zssm_uses_temporary_model(app: App, respx_mock: MockRouter, zssm_model, mocker):
    """--model 仅为本次解释覆盖专用模型。"""
    from src.plugins.llm.config import ModelConfig, plugin_config

    default_model, _ = zssm_model
    temporary_model = ModelConfig(
        name="temporary",
        provider="openai_chat_completions",
        base_url="https://temporary.example.com",
        api_key="sk-temporary",
    )
    mocker.patch.object(plugin_config, "models", [default_model, temporary_model])
    from src.plugins.llm.data_source import set_available_model_names

    await set_available_model_names("QQClient_10000", ["test-model", "temporary"])
    route = respx_mock.post("https://temporary.example.com/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "temporary",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": '{"output":"临时模型解释","keywords":[],"blocked":false}',
                        },
                    }
                ],
            },
        )
    )

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("zssm --model temporary Python GIL"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message(MessageSegment.reply(1))
            + "临时模型解释\n\n---\n模型　temporary  \n统计　5.1s · 输入 0 · 输出 0 · 缓存 0 · 共 0",
            True,
        )

    payload = json.loads(route.calls[0].request.content)
    user_message = next(message for message in payload["messages"] if message["role"] == "user")
    user_data = json.loads(user_message["content"])
    assert user_data["target"] == "Python GIL"


async def test_zssm_rejects_unknown_temporary_model(app: App, zssm_model):
    """临时指定未启用模型时在调用前给出明确提示。"""
    from src.plugins.llm.plugins.zssm import zssm_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("zssm --model missing Python GIL"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message(MessageSegment.reply(1)) + "本群未启用解释模型：missing，可用：test-model",
            True,
        )
        ctx.should_finished(zssm_cmd)


async def test_zssm_rejects_vision_only_temporary_model(app: App, zssm_model, mocker):
    """仅视觉模型不能作为临时解释模型处理文本。"""
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names
    from src.plugins.llm.plugins.zssm import zssm_cmd

    default_model, _ = zssm_model
    vision_model = ModelConfig(name="vision-only", capabilities={"vision"})
    mocker.patch.object(plugin_config, "models", [default_model, vision_model])
    await set_available_model_names("QQClient_10000", ["test-model", "vision-only"])

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("zssm --model vision-only Python GIL"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message(MessageSegment.reply(1)) + "解释模型 vision-only 未声明 text 能力，不能用于文本解释",
            True,
        )
        ctx.should_finished(zssm_cmd)


@respx.mock(assert_all_called=True)
async def test_zssm_explains_text_with_group_model(app: App, respx_mock: MockRouter, zssm_model, mocker):
    """直接输入文本时使用本群解释模型、专用提示词并关闭工具。"""
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names, set_zssm_model_name

    default_model, _ = zssm_model
    explain_model = ModelConfig(
        name="explain",
        model="explain-upstream",
        provider="openai_chat_completions",
        base_url="https://api.example.com",
        api_key="sk-test",
    )
    mocker.patch.object(plugin_config, "models", [default_model, explain_model])
    await set_available_model_names("QQClient_10000", ["test-model", "explain"])
    await set_zssm_model_name("QQClient_10000", "explain")
    route = respx_mock.post("https://api.example.com/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "explain-upstream",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(
                                {
                                    "output": "GIL 是 CPython 用来协调字节码执行的一把全局锁。",
                                    "keywords": ["Python", "GIL"],
                                    "blocked": False,
                                },
                                ensure_ascii=False,
                            ),
                            "reasoning_content": "这段推理不应展示",
                        },
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )
    )

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("zssm Python GIL"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message(MessageSegment.reply(1))
            + (
                "关键词：Python | GIL\n\nGIL 是 CPython 用来协调字节码执行的一把全局锁。"
                "\n\n---\n模型　explain-upstream  \n"
                "统计　5.1s · 输入 10 · 输出 5 · 缓存 0 · 共 15"
            ),
            True,
        )

    payload = json.loads(route.calls[0].request.content)
    assert payload["model"] == "explain-upstream"
    assert "tools" not in payload
    assert payload["messages"][0]["role"] == "system"
    assert "不可信数据" in payload["messages"][0]["content"]
    user_data = json.loads(payload["messages"][1]["content"])
    assert user_data == {
        "target": "Python GIL",
        "focus": "",
        "image_count": 0,
        "image_descriptions": "",
        "resources": [],
    }

    _, reaction = zssm_model
    assert reaction.await_args_list == [
        call("thinking", message_id="1"),
        call("done", message_id="1"),
    ]


@respx.mock(assert_all_called=True)
async def test_zssm_agent_option_enables_web_search(app: App, respx_mock: MockRouter, zssm_model):
    """-a 为本次解释开放包含网页搜索在内的工具。"""
    route = respx_mock.post("https://api.example.com/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": '{"output":"联网解释","keywords":[],"blocked":false}',
                        },
                    }
                ],
            },
        )
    )

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("zssm -a Python 3.14 新特性"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message(MessageSegment.reply(1))
            + "联网解释\n\n---\n模型　test-model  \n统计　5.1s · 输入 0 · 输出 0 · 缓存 0 · 共 0",
            True,
        )

    payload = json.loads(route.calls[0].request.content)
    tool_names = {tool["function"]["name"] for tool in payload["tools"]}
    assert {"web_search", "web_fetch"} <= tool_names
    user_message = next(message for message in payload["messages"] if message["role"] == "user")
    user_data = json.loads(user_message["content"])
    assert user_data["target"] == "Python 3.14 新特性"


@respx.mock(assert_all_called=True)
async def test_zssm_render_option_sends_markdown_image(
    app: App,
    respx_mock: MockRouter,
    zssm_model,
    mocker,
):
    """-r 将本次解释渲染成图片，并保持回复关系。"""
    rendered = b"\x89PNG\r\n\x1a\nrendered"
    render_markdown = mocker.patch("src.plugins.llm.handler.try_render_markdown", return_value=rendered)
    respx_mock.post("https://api.example.com/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": '{"output":"**图片解释**","keywords":[],"blocked":false}',
                        },
                    }
                ],
            },
        )
    )

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("zssm -r Python GIL"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message(MessageSegment.reply(1)) + MessageSegment.image(rendered),
            True,
        )

    render_markdown.assert_awaited_once_with(
        "**图片解释**\n\n---\n模型　test-model  \n统计　5.1s · 输入 0 · 输出 0 · 缓存 0 · 共 0"
    )


async def test_zssm_logs_provider_failure_as_warning(app: App, zssm_model, mocker):
    """可预期的上游协议错误记录阶段和详情，但不输出异常堆栈。"""
    from src.plugins.llm.plugins.zssm import zssm_cmd
    from src.plugins.llm.providers import ProviderError

    error = ProviderError("服务返回无效 JSON（HTTP 502，Content-Type=text/html，响应 0 字节）")
    handler = mocker.Mock(log_id="abcd1234")
    handler.ask = mocker.AsyncMock(side_effect=error)
    mocker.patch("src.plugins.llm.plugins.zssm.LLMHandler", return_value=handler)
    zssm_logger = mocker.patch("src.plugins.llm.plugins.zssm.logger")

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("zssm Python GIL"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message(MessageSegment.reply(1)) + f"解释失败：{error}",
            True,
        )
        ctx.should_finished(zssm_cmd)

    zssm_logger.warning.assert_called_once_with(
        "解释模式失败（会话={}，模型={}，阶段={}，错误类型={}，错误={}）",
        "abcd1234",
        "test-model",
        "解释模型请求",
        "ProviderError",
        error,
    )
    zssm_logger.opt.assert_not_called()


async def test_zssm_logs_unexpected_failure_as_error(app: App, zssm_model, mocker):
    """未预期的程序异常以 ERROR 记录上下文和堆栈。"""
    from src.plugins.llm.plugins.zssm import zssm_cmd

    error = RuntimeError("unexpected")
    handler = mocker.Mock(log_id="abcd1234")
    handler.ask = mocker.AsyncMock(side_effect=error)
    mocker.patch("src.plugins.llm.plugins.zssm.LLMHandler", return_value=handler)
    zssm_logger = mocker.patch("src.plugins.llm.plugins.zssm.logger")

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(message=Message("zssm Python GIL"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message(MessageSegment.reply(1)) + "解释失败，请稍后重试",
            True,
        )
        ctx.should_finished(zssm_cmd)

    zssm_logger.warning.assert_not_called()
    zssm_logger.opt.assert_called_once_with(exception=error)
    zssm_logger.opt.return_value.error.assert_called_once_with(
        "解释模式出现未预期的错误（会话={}，模型={}，阶段={}，错误类型={}）",
        "abcd1234",
        "test-model",
        "解释模型请求",
        "RuntimeError",
    )


@respx.mock(assert_all_called=True)
async def test_zssm_separates_reply_and_focus(app: App, respx_mock: MockRouter, zssm_model):
    """回复消息是解释目标，命令后的文本只作为关注点。"""
    route = respx_mock.post("https://api.example.com/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": '{"output":"解释结果","keywords":[],"blocked":false}',
                        },
                    }
                ],
            },
        )
    )
    reply = OneBotReply(
        time=1,
        message_type="group",
        message_id=99,
        real_id=99,
        sender=Sender(user_id=20, nickname="群友"),
        message=Message("量子纠缠与贝尔不等式"),
    )

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)
        event = fake_group_message_event_v11(
            message=Message("zssm 重点解释贝尔不等式"),
            reply=reply,
        )

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            Message(MessageSegment.reply(1))
            + "解释结果\n\n---\n模型　test-model  \n统计　5.1s · 输入 0 · 输出 0 · 缓存 0 · 共 0",
            True,
        )

    payload = json.loads(route.calls[0].request.content)
    user_data = json.loads(payload["messages"][1]["content"])
    assert user_data["target"] == "量子纠缠与贝尔不等式"
    assert user_data["focus"] == "重点解释贝尔不等式"


def test_explain_response_formatting(app: App):
    """结构化输出支持代码块、去重关键词和拒答。"""
    from src.plugins.llm.plugins.zssm.data_source import format_explain_response

    assert (
        format_explain_response('```json\n{"output":"解释","keywords":["A","A","B"],"blocked":false}\n```')
        == "关键词：A | B\n\n解释"
    )
    assert format_explain_response('{"output":"","keywords":[],"blocked":true}') == "（抱歉，我现在还不会这个）"
    assert format_explain_response("普通文本") == "普通文本"


def test_extract_urls(app: App):
    """只提取消息里实际出现的 HTTP(S) 地址并去重。"""
    from src.plugins.llm.plugins.zssm.data_source import extract_urls

    assert extract_urls(
        "查看 https://example.com/a?q=1。再看 https://example.com/b)",
        "重复 https://example.com/a?q=1",
    ) == ["https://example.com/a?q=1", "https://example.com/b"]


async def test_fetch_images_uses_multimodal_input(app: App, mocker):
    """解释模式复用 LLM 图片结构，不再调用独立视觉模型。"""
    from nonebot_plugin_alconna.uniseg import Image

    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.plugins.zssm.data_source import fetch_images

    png = b"\x89PNG\r\n\x1a\n" + b"test"
    event = mocker.Mock()
    log_info = mocker.patch("src.plugins.llm.plugins.zssm.data_source.logger.info")
    contents = await fetch_images([Image(raw=png)], event, mocker.Mock(), {})

    assert len(contents) == 1
    assert contents[0].data == png
    assert contents[0].mimetype == "image/png"
    assert log_info.call_count == 2

    mocker.patch.object(plugin_config, "zssm_max_images", 1)
    with pytest.raises(ValueError, match="最多 1 张"):
        await fetch_images([Image(raw=png), Image(raw=png)], event, mocker.Mock(), {})


@respx.mock(assert_all_called=True)
async def test_vision_model_describes_images(app: App, respx_mock: MockRouter, zssm_model):
    """文本解释模型可复用模型列表中的独立视觉模型。"""
    from src.plugins.llm.plugins.zssm.data_source import describe_images
    from src.plugins.llm.schemas import ImageContent

    model, _ = zssm_model
    model.capabilities.add("vision")

    route = respx_mock.post("https://api.example.com/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "vision-model",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "图片 1：蓝色方块旁写着数字 42。"},
                    }
                ],
                "usage": {"prompt_tokens": 8, "completion_tokens": 6},
            },
        )
    )
    image = ImageContent.from_bytes(b"\x89PNG\r\n\x1a\n" + b"test")

    description, completion = await describe_images("test-model", [image])

    assert description == "图片 1：蓝色方块旁写着数字 42。"
    assert completion.model == "vision-model"
    assert completion.usage.total_tokens == 14
    payload = json.loads(route.calls[0].request.content)
    assert "tools" not in payload
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["content"][0]["type"] == "text"
    assert payload["messages"][1]["content"][1]["type"] == "image_url"


def test_model_capability_selects_single_or_two_stage_vision(app: App, mocker):
    """多模态解释模型只调用一次，文本模型才选择独立视觉模型。"""
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.plugins.zssm.data_source import resolve_vision_fallback

    multimodal = ModelConfig(name="multimodal", capabilities={"text", "vision"})
    text = ModelConfig(name="text")
    vision = ModelConfig(name="vision", capabilities={"vision"})
    mocker.patch.object(plugin_config, "models", [multimodal, text, vision])
    assert resolve_vision_fallback("multimodal", "vision", has_images=True) == ""
    assert resolve_vision_fallback("text", "vision", has_images=True) == "vision"
    assert resolve_vision_fallback("text", "vision", has_images=False) == ""

    with pytest.raises(ValueError, match="本群没有已启用并声明 vision 能力的模型"):
        resolve_vision_fallback("text", "", has_images=True)


async def test_private_resource_url_is_rejected(app: App):
    """外部资料读取不能访问本机和内网地址。"""
    from src.plugins.llm.tools.web import ResourceError, _ensure_public_url

    with pytest.raises(ResourceError, match="非公网地址"):
        await _ensure_public_url("http://127.0.0.1/admin")
    with pytest.raises(ResourceError, match="非公网地址"):
        await _ensure_public_url("http://[::1]/admin")


async def test_domain_fake_ip_is_allowed_without_allowing_ip_literal(app: App, mocker):
    """域名解析可使用代理 fake-ip，但用户直接填写保留地址仍会被拒绝。"""
    import ipaddress

    from src.plugins.llm.tools.web import ResourceError, _ensure_public_url

    resolve = mocker.patch(
        "src.plugins.llm.tools.web._resolve_host_addresses",
        return_value={ipaddress.ip_address("198.18.1.2")},
    )

    await _ensure_public_url("https://example.com/article")
    resolve.assert_awaited_once_with("example.com", 443)

    with pytest.raises(ResourceError, match="非公网地址"):
        await _ensure_public_url("https://198.18.1.2/article")


async def test_domain_private_ip_outside_fake_range_is_rejected(app: App, mocker):
    """普通域名解析到真实私网时仍阻止访问。"""
    import ipaddress

    from src.plugins.llm.tools.web import ResourceError, _ensure_public_url

    mocker.patch(
        "src.plugins.llm.tools.web._resolve_host_addresses",
        return_value={ipaddress.ip_address("192.168.1.10")},
    )

    with pytest.raises(ResourceError, match="非公网地址"):
        await _ensure_public_url("https://internal.example.com/admin")


async def test_resource_operations_are_logged_without_url_details(app: App, mocker):
    """资源读取记录主机、结果和长度，但不把路径或查询参数写入日志。"""
    from src.plugins.llm.plugins.zssm.data_source import load_resources
    from src.plugins.llm.tools.web import ResourceContent

    read_resource = mocker.patch(
        "src.plugins.llm.plugins.zssm.data_source.read_resource",
        return_value=ResourceContent("https://cdn.example.com/final", "web_page", "正文"),
    )
    log_info = mocker.patch("src.plugins.llm.plugins.zssm.data_source.logger.info")

    result = await load_resources("https://example.com/private/path?token=secret")

    assert result == [ResourceContent("https://cdn.example.com/final", "web_page", "正文")]
    read_resource.assert_awaited_once_with("https://example.com/private/path?token=secret")
    log_text = " ".join(str(item) for item in log_info.call_args_list)
    assert "example.com" in log_text
    assert "cdn.example.com" in log_text
    assert "private/path" not in log_text
    assert "token=secret" not in log_text


@respx.mock(assert_all_called=True)
async def test_read_web_resource_extracts_visible_text(app: App, respx_mock: MockRouter, mocker):
    """网页读取不执行脚本，只把可见文本交给模型。"""
    from src.plugins.llm.tools.web import read_resource

    mocker.patch("src.plugins.llm.tools.web._ensure_public_url")
    respx_mock.get("https://example.com/article").mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text="<html><head><script>secret()</script></head><body><h1>标题</h1><p>正文 内容</p></body></html>",
        )
    )

    result = await read_resource("https://example.com/article")

    assert result.url == "https://example.com/article"
    assert result.kind == "web_page"
    assert result.content == "标题\n正文 内容"


@respx.mock(assert_all_called=True)
async def test_resource_redirect_target_is_revalidated(app: App, respx_mock: MockRouter, mocker):
    """公开链接不能通过重定向绕过内网地址检查。"""
    from src.plugins.llm.tools.web import ResourceError, read_resource

    validate = mocker.patch(
        "src.plugins.llm.tools.web._ensure_public_url",
        side_effect=[None, ResourceError("不允许访问本机、内网或非公网地址")],
    )
    respx_mock.get("https://example.com/redirect").mock(
        return_value=httpx.Response(302, headers={"location": "http://127.0.0.1/admin"})
    )

    with pytest.raises(ResourceError, match="非公网地址"):
        await read_resource("https://example.com/redirect")

    assert [item.args[0] for item in validate.await_args_list] == [
        "https://example.com/redirect",
        "http://127.0.0.1/admin",
    ]


def test_pdf_resource_text_extraction(app: App):
    """PDF 在内存中解析并提取文本。"""
    from src.plugins.llm.tools.web import _extract_pdf_text

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Hello PDF")
    data = document.tobytes()
    document.close()

    assert _extract_pdf_text(data) == "Hello PDF"
