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

from tests.fake import fake_group_message_event_v11


@pytest.fixture
def zssm_model(mocker):
    """配置解释模式测试模型。"""
    from src.plugins.llm.config import ModelConfig, plugin_config

    model = ModelConfig(
        name="test-model",
        provider="chat",
        base_url="https://api.example.com",
        api_key="sk-test",
    )
    mocker.patch.object(plugin_config, "models", [model])
    mocker.patch.object(plugin_config, "zssm_model", "")
    mocker.patch("src.plugins.llm.handler.perf_counter", side_effect=[10.0, 15.1])
    reaction = mocker.patch("src.plugins.llm.plugins.zssm.send_reaction")
    return model, reaction


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


@respx.mock(assert_all_called=True)
async def test_zssm_explains_text_without_tools(app: App, respx_mock: MockRouter, zssm_model):
    """直接输入文本时使用专用提示词、关闭工具并格式化输出。"""
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
            Message(
                "关键词：Python | GIL\n\nGIL 是 CPython 用来协调字节码执行的一把全局锁。"
                "\n\n--- 5.1s  test-model  I:10 O:5 A:15 C:0"
            ),
            True,
        )

    payload = json.loads(route.calls[0].request.content)
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
            Message(MessageSegment.reply(99)) + "解释结果\n\n--- 5.1s  test-model  I:0 O:0 A:0 C:0",
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

    multimodal = ModelConfig(name="multimodal", capabilities={"vision"})
    text = ModelConfig(name="text")
    vision = ModelConfig(name="vision", capabilities={"vision"})
    mocker.patch.object(plugin_config, "models", [multimodal, text, vision])
    mocker.patch.object(plugin_config, "zssm_vision_model", "vision")

    assert resolve_vision_fallback("multimodal", has_images=True) == ""
    assert resolve_vision_fallback("text", has_images=True) == "vision"
    assert resolve_vision_fallback("text", has_images=False) == ""

    mocker.patch.object(plugin_config, "zssm_vision_model", "")
    with pytest.raises(ValueError, match="LLM__ZSSM_VISION_MODEL"):
        resolve_vision_fallback("text", has_images=True)


async def test_private_resource_url_is_rejected(app: App):
    """外部资料读取不能访问本机和内网地址。"""
    from src.plugins.llm.plugins.zssm.data_source import ResourceError, _ensure_public_url

    with pytest.raises(ResourceError, match="非公网地址"):
        await _ensure_public_url("http://127.0.0.1/admin")
    with pytest.raises(ResourceError, match="非公网地址"):
        await _ensure_public_url("http://[::1]/admin")


async def test_domain_fake_ip_is_allowed_without_allowing_ip_literal(app: App, mocker):
    """域名解析可使用代理 fake-ip，但用户直接填写保留地址仍会被拒绝。"""
    import ipaddress

    from src.plugins.llm.plugins.zssm.data_source import ResourceError, _ensure_public_url

    resolve = mocker.patch(
        "src.plugins.llm.plugins.zssm.data_source._resolve_host_addresses",
        return_value={ipaddress.ip_address("198.18.1.2")},
    )

    await _ensure_public_url("https://example.com/article")
    resolve.assert_awaited_once_with("example.com", 443)

    with pytest.raises(ResourceError, match="非公网地址"):
        await _ensure_public_url("https://198.18.1.2/article")


async def test_domain_private_ip_outside_fake_range_is_rejected(app: App, mocker):
    """普通域名解析到真实私网时仍阻止访问。"""
    import ipaddress

    from src.plugins.llm.plugins.zssm.data_source import ResourceError, _ensure_public_url

    mocker.patch(
        "src.plugins.llm.plugins.zssm.data_source._resolve_host_addresses",
        return_value={ipaddress.ip_address("192.168.1.10")},
    )

    with pytest.raises(ResourceError, match="非公网地址"):
        await _ensure_public_url("https://internal.example.com/admin")


async def test_resource_operations_are_logged_without_url_details(app: App, mocker):
    """资源读取记录主机、结果和长度，但不把路径或查询参数写入日志。"""
    from src.plugins.llm.plugins.zssm.data_source import ResourceContent, load_resources

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
    from src.plugins.llm.plugins.zssm.data_source import read_resource

    mocker.patch("src.plugins.llm.plugins.zssm.data_source._ensure_public_url")
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
    from src.plugins.llm.plugins.zssm.data_source import ResourceError, read_resource

    validate = mocker.patch(
        "src.plugins.llm.plugins.zssm.data_source._ensure_public_url",
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
    from src.plugins.llm.plugins.zssm.data_source import _extract_pdf_text

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Hello PDF")
    data = document.tobytes()
    document.close()

    assert _extract_pdf_text(data) == "Hello PDF"
