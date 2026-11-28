"""绘图命令和图片服务的端到端回归测试。"""

import base64
import json
from io import BytesIO

import httpx
import pytest
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App
from PIL import Image as PILImage
from respx import MockRouter

from tests.fake import fake_group_message_event_v11

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+yA2sAAAAASUVORK5CYII=")
SESSION = "QQClient_10000"


@pytest.mark.parametrize("command", ["/draw", "/chat -d"])
@pytest.mark.parametrize(
    "description", ["画一只猫", "画一只猫，要有动态光影，写着“高清 GIF 640×480”，时间是12:30，不要PNG"]
)
async def test_image_only_group_can_draw(app: App, mocker, respx_mock: MockRouter, command: str, description: str):
    from nonebot_plugin_alconna import Image, UniMessage

    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names

    painter = ModelConfig(name="painter", provider="openai_images", model="actual-image-model", timeout=99)
    mocker.patch.object(plugin_config, "models", [painter])
    mocker.patch.object(plugin_config, "base_url", "https://images.example.com/v1")
    mocker.patch.object(plugin_config, "api_key", "image-token")
    mocker.patch("src.plugins.llm.dialogue.send_reaction")
    send = mocker.patch.object(UniMessage, "send", autospec=True)
    await set_available_model_names(SESSION, [painter.name])
    route = respx_mock.post("https://images.example.com/v1/images/generations").mock(
        return_value=httpx.Response(
            200,
            json={"data": [{"b64_json": base64.b64encode(PNG).decode()}], "usage": {"input_tokens": 7}},
        )
    )

    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter))
        ctx.receive_event(bot, fake_group_message_event_v11(message=Message(f"{command} {description}"), user_id=10))

    assert route.call_count == 1
    assert route.calls.last.request.headers["Authorization"] == "Bearer image-token"
    assert json.loads(route.calls.last.request.content) == {"model": "actual-image-model", "prompt": description}
    assert send.await_args_list[0].args[0].get(Image)[0].raw == PNG
    summary = send.await_args_list[1].args[0].extract_plain_text()
    assert "painter" in summary
    assert "输入 7" in summary


def make_image(output_format: str, *, frames: int = 1, size: tuple[int, int] = (16, 12)) -> bytes:
    file = BytesIO()
    images = [PILImage.new("RGB", size, (index * 16, 0, 0)) for index in range(frames)]
    images[0].save(file, format=output_format, save_all=frames > 1, append_images=images[1:], duration=100)
    return file.getvalue()


def image_response(image: bytes) -> httpx.Response:
    return httpx.Response(
        200, json={"data": [{"b64_json": base64.b64encode(image).decode()}], "usage": {"input_tokens": 7}}
    )


async def test_draw_does_not_infer_output_from_quoted_caption(app: App, mocker, respx_mock: MockRouter):
    from nonebot.adapters.onebot.v11.event import Reply, Sender
    from nonebot_plugin_alconna import UniMessage

    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names

    model = ModelConfig(
        name="painter",
        provider="openai_images",
        base_url="https://images.example.com/v1",
        image_output_formats={"png"},
    )
    mocker.patch.object(plugin_config, "models", [model])
    mocker.patch("src.plugins.llm.dialogue.send_reaction")
    send = mocker.patch.object(UniMessage, "send", autospec=True)
    await set_available_model_names(SESSION, [model.name])
    png = make_image("PNG")
    route = respx_mock.post("https://images.example.com/v1/images/generations").mock(return_value=image_response(png))
    previous = Reply(
        time=1,
        message_type="group",
        message_id=99,
        real_id=99,
        sender=Sender(user_id=20, nickname="群友"),
        message=Message("导出 1920x1080 JPEG"),
    )

    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter), self_id="123456")
        ctx.receive_event(
            bot,
            fake_group_message_event_v11(
                self_id=123456,
                message_id=100_907,
                message=Message("/draw 画一张 PNG 猫头像"),
                user_id=10,
                reply=previous,
            ),
        )

    assert route.call_count == 1
    payload = json.loads(route.calls.last.request.content)
    assert payload["output_format"] == "png"
    assert "size" not in payload
    assert "导出 1920x1080 JPEG" in payload["prompt"]
    assert "画一张 PNG 猫头像" in payload["prompt"]
    assert send.await_count == 2


@pytest.mark.parametrize("command", ["/draw", "/chat -d"])
@pytest.mark.parametrize("selector", ["", "--image-model animator", "--model animator"])
async def test_explicit_gif_and_size_choose_capable_gateway(
    app: App, mocker, respx_mock: MockRouter, command, selector
):
    from nonebot_plugin_alconna import Image, UniMessage

    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names, set_image_model_name

    text = ModelConfig(name="chat", base_url="https://chat.example.com/v1")
    still = ModelConfig(
        name="still",
        provider="openai_images",
        base_url="https://still.example.com/v1",
        extra_body={"output_format": "png", "size": "16x12"},
    )
    animator = ModelConfig(
        name="animator",
        model="remote-animator",
        provider="openai_images",
        base_url="https://gif.example.com/v1",
        api_key="gif-token",
        image_output_formats={"gif"},
        image_sizes={"16x12"},
        extra_body={"output_format": "png", "size": "8x8", "frames": 2, "frame_duration_ms": 100},
    )
    mocker.patch.object(plugin_config, "models", [text, still, animator])
    mocker.patch("src.plugins.llm.dialogue.send_reaction")
    send = mocker.patch.object(UniMessage, "send", autospec=True)
    await set_available_model_names(SESSION, ["chat", "still", "animator"])
    await set_image_model_name(SESSION, "still")
    gif = make_image("GIF", frames=2)
    route = respx_mock.post("https://gif.example.com/v1/images/generations").mock(return_value=image_response(gif))

    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter))
        request = f"{command} {selector} --format gif --size 16x12 画猫".replace("  ", " ")
        ctx.receive_event(bot, fake_group_message_event_v11(message=Message(request), user_id=10))

    assert route.call_count == 1
    upstream = route.calls.last.request
    assert upstream.headers["Authorization"] == "Bearer gif-token"
    assert json.loads(upstream.content) == {
        "model": "remote-animator",
        "prompt": "画猫",
        "output_format": "gif",
        "size": "16x12",
        "frames": 2,
        "frame_duration_ms": 100,
    }
    assert send.await_args_list[0].args[0].get(Image)[0].raw == gif
    assert "animator" in send.await_args_list[1].args[0].extract_plain_text()
    assert "GIF 16x12 / 2 帧" in send.await_args_list[1].args[0].extract_plain_text()


@pytest.mark.parametrize(
    ("command", "description", "image_format", "size"),
    [
        ("/draw", "给你自己画一张1024方形的魔理沙简笔动态头像", "gif", (1024, 1024)),
        ("/chat -d", "设计一张128像素见方的动态贴纸", "gif", (128, 128)),
        ("/draw", "渲染一张 640 × 480 的 WebP 横幅", "webp", (640, 480)),
        ("/draw", "导出 PNG，宽320像素、高240像素的宣传图", "png", (320, 240)),
        ("/draw --format jpeg --size 40x30", "9:16 的 128 方形 GIF 动图", "jpeg", (40, 30)),
        ("/draw", "Make an animated icon, 96px square", "gif", (96, 96)),
    ],
)
async def test_draw_understands_natural_output_requirements(
    app: App, mocker, respx_mock: MockRouter, command, description, image_format, size
):
    from nonebot_plugin_alconna import Image, UniMessage

    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names

    pixels = f"{size[0]}x{size[1]}"
    model = ModelConfig(
        name="painter",
        provider="openai_images",
        base_url="https://image.example.com/v1",
        image_output_formats={image_format},
        image_sizes={pixels},
    )
    mocker.patch.object(plugin_config, "models", [model])
    mocker.patch("src.plugins.llm.dialogue.send_reaction")
    send = mocker.patch.object(UniMessage, "send", autospec=True)
    await set_available_model_names(SESSION, ["painter"])
    image = make_image(image_format.upper(), size=size, frames=2 if image_format == "gif" else 1)
    route = respx_mock.post("https://image.example.com/v1/images/generations").mock(return_value=image_response(image))

    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter))
        ctx.receive_event(bot, fake_group_message_event_v11(message=Message(f"{command} {description}"), user_id=10))

    assert route.call_count == 1
    assert json.loads(route.calls.last.request.content) == {
        "model": "painter",
        "prompt": description,
        "output_format": image_format,
        "size": pixels,
    }
    assert send.await_args_list[0].args[0].get(Image)[0].raw == image
    assert f"{image_format.upper()} {pixels}" in send.await_args_list[1].args[0].extract_plain_text()


@pytest.mark.parametrize(
    ("description", "default_size", "selected_name", "output_format", "size"),
    [
        ("画一张16:9的gif头像", "1536x1024", "painter", "gif", (1820, 1024)),
        ("输出9：16的PNG竖版海报", "auto", "painter", "png", (1024, 1820)),
        ("画一张32:18（16:9）的GIF头像", "1200x900", "alternative", "gif", (1600, 900)),
        ("画一张4:3，尺寸960×720的PNG横幅", "auto", "painter", "png", (960, 720)),
    ],
)
async def test_draw_preserves_default_short_edge_for_aspect_ratio(
    app: App, mocker, respx_mock: MockRouter, description, default_size, selected_name, output_format, size
):
    from nonebot_plugin_alconna import Image, UniMessage

    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names, set_image_model_name

    pixels = f"{size[0]}x{size[1]}"
    painter = ModelConfig(
        name="painter",
        provider="openai_images",
        base_url="https://image.example.com/v1",
        image_output_formats={output_format},
        image_sizes={pixels} if selected_name == "painter" else {"1600x900"},
        extra_body={"size": default_size if selected_name == "painter" else "1536x1024"},
    )
    alternative = ModelConfig(
        name="alternative",
        provider="openai_images",
        base_url="https://alternative.example.com/v1",
        image_output_formats={output_format},
        image_sizes={pixels},
        extra_body={"size": default_size},
    )
    models = [painter] if selected_name == "painter" else [painter, alternative]
    mocker.patch.object(plugin_config, "models", models)
    mocker.patch("src.plugins.llm.dialogue.send_reaction")
    send = mocker.patch.object(UniMessage, "send", autospec=True)
    await set_available_model_names(SESSION, [model.name for model in models])
    await set_image_model_name(SESSION, "painter")
    image = make_image(output_format.upper(), size=size, frames=2 if output_format == "gif" else 1)
    base_url = next(model.base_url for model in models if model.name == selected_name)
    route = respx_mock.post(f"{base_url}/images/generations").mock(return_value=image_response(image))

    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter))
        ctx.receive_event(bot, fake_group_message_event_v11(message=Message(f"/draw {description}"), user_id=10))

    assert route.call_count == 1
    assert json.loads(route.calls.last.request.content) == {
        "model": selected_name,
        "prompt": description,
        "output_format": output_format,
        "size": pixels,
    }
    assert send.await_args_list[0].args[0].get(Image)[0].raw == image
    assert f"{output_format.upper()} {pixels}" in send.await_args_list[1].args[0].extract_plain_text()


@pytest.mark.parametrize(
    ("description", "error"),
    [
        ("做一张512方形的动图", "本群没有满足绘图要求的模型（要求 GIF / 512x512；painter：未声明支持 gif 格式）"),
        ("尺寸 512x512 或 1024x1024 的猫", "图片描述包含多个尺寸要求，请用 --size 明确指定"),
        ("输出 PNG 和 JPEG 的头像", "图片描述包含多个格式要求，请用 --format 明确指定"),
        ("画一张16:9或4:3的头像", "图片描述包含多个宽高比要求，请用 --size 明确指定"),
        ("画一张16:9的960x720头像", "图片描述的宽高比 16:9 与尺寸 960x720 冲突"),
        ("画一张16:9的高清头像", "本群没有满足绘图要求的模型（要求 16:9；painter：未声明支持 5120x2880 尺寸）"),
        ("画一张16:9的头像", "本群没有满足绘图要求的模型（要求 16:9；painter：未声明支持 1820x1024 尺寸）"),
    ],
)
async def test_draw_rejects_unusable_natural_output_before_network(
    app: App, mocker, respx_mock: MockRouter, description, error
):
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names

    model = ModelConfig(name="painter", provider="openai_images", base_url="https://image.example.com/v1")
    mocker.patch.object(plugin_config, "models", [model])
    await set_available_model_names(SESSION, ["painter"])
    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter))
        event = fake_group_message_event_v11(message=Message(f"/draw {description}"), user_id=10)
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, error, True, at_sender=True)
    assert not respx_mock.calls


@pytest.mark.parametrize(
    ("options", "error"),
    [
        ("--image-model missing", "本群未启用的模型：missing"),
        ("--image-model painter --model other", "--image-model 与绘图别名 --model 指定的模型冲突"),
        ("--hd --size 16x12", "--hd 固定为 2880x2880，与 --size 16x12 冲突"),
        ("--image-model painter --format gif", "本群没有满足绘图要求的模型（要求 GIF；painter：未声明支持 gif 格式）"),
        ("--image-model painter -c", "本群没有满足绘图要求的模型（painter：只支持生成，不支持参考图或多轮续画）"),
    ],
)
async def test_reject_unsupported_explicit_request_before_network(
    app: App, mocker, respx_mock: MockRouter, options, error
):
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names

    painter = ModelConfig(name="painter", provider="openai_images", base_url="https://image.example.com/v1")
    mocker.patch.object(plugin_config, "models", [painter])
    await set_available_model_names(SESSION, ["painter"])
    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter))
        event = fake_group_message_event_v11(message=Message(f"/draw {options} 画猫"), user_id=10)
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, error, True, at_sender=True)
    assert not respx_mock.calls


@pytest.mark.parametrize(
    ("requested_format", "requested_size", "image", "error"),
    [
        ("gif", "16x12", make_image("PNG"), "要求 gif，服务返回 png"),
        ("gif", "16x12", make_image("GIF"), "要求多帧 GIF，服务返回 1 帧"),
        ("png", "16x12", make_image("PNG", size=(32, 12)), "要求 16x12，服务返回 32x12"),
    ],
)
async def test_bad_output_does_not_retry_and_records_returned_usage(
    app: App,
    mocker,
    respx_mock: MockRouter,
    requested_format,
    requested_size,
    image,
    error,
):
    from src.plugins.llm.config import ModelConfig
    from src.plugins.llm.image_service import ImageRequirements, ImageTask
    from src.plugins.llm.providers import ProviderError

    model = ModelConfig(
        name="painter",
        provider="openai_images",
        base_url="https://image.example.com/v1",
        image_output_formats={"gif", "png"},
        image_sizes={"16x12"},
    )
    route = respx_mock.post("https://image.example.com/v1/images/generations").mock(return_value=image_response(image))
    log = mocker.patch("src.plugins.llm.image_service.logger.info")
    task = ImageTask(model, "session", requirements=ImageRequirements.from_options(requested_format, requested_size))
    with pytest.raises(ProviderError, match=error):
        await task.run("画猫")
    assert route.call_count == 1
    log.assert_called_once()
    assert "输入 7" in log.call_args.args[1]


async def test_draw_context_replays_native_image_at_same_responses_connection(app: App, mocker, respx_mock: MockRouter):
    from nonebot_plugin_alconna import UniMessage

    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names, set_image_model_name

    still = ModelConfig(name="still", provider="openai_images", base_url="https://still.example.com/v1")
    response_model = ModelConfig(
        name="context-painter",
        model="gpt-picture",
        provider="openai_responses",
        base_url="https://painter.example.com/v1",
        api_key="painter-token",
        capabilities={"image_generation"},
        extra_body={"size": "16x12", "frames": 2, "frame_duration_ms": 100},
    )
    mocker.patch.object(plugin_config, "models", [still, response_model])
    await set_available_model_names(SESSION, ["still", "context-painter"])
    await set_image_model_name(SESSION, "still")
    mocker.patch("src.plugins.llm.dialogue.send_reaction")
    mocker.patch.object(UniMessage, "send", autospec=True)
    native_item = {
        "type": "image_generation_call",
        "id": "ig_1",
        "status": "completed",
        "result": base64.b64encode(PNG).decode(),
    }
    route = respx_mock.post("https://painter.example.com/v1/responses").mock(
        return_value=httpx.Response(200, json={"status": "completed", "output": [native_item]})
    )
    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter))
        event = fake_group_message_event_v11(message=Message("/draw -c 画猫"), user_id=10)
        reply = (UniMessage.text("改成蓝色"), "43", event, bot, {})
        end = (UniMessage.text("结束"), "44", event, bot, {})
        mocker.patch("nonebot_plugin_waiter.prompt", side_effect=[reply, end])
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "已结束绘图", True)

    assert route.call_count == 2
    first, second = [json.loads(call.request.content) for call in route.calls]
    assert first["model"] == second["model"] == "gpt-picture"
    for call in route.calls:
        assert call.request.headers["Authorization"] == "Bearer painter-token"
    assert route.calls[0].request.headers["X-Session-Affinity"] == route.calls[1].request.headers["X-Session-Affinity"]
    assert first["tools"] == [{"type": "image_generation", "size": "16x12"}]
    assert "frames" not in first
    assert "frame_duration_ms" not in first
    assert second["input"][1] == native_item
    assert second["input"][2]["content"] == [{"type": "input_text", "text": "改成蓝色"}]


async def test_chat_image_limit_and_failed_summary_still_deliver_image(app: App, mocker, respx_mock: MockRouter):
    from nonebot_plugin_alconna import Image, UniMessage

    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names

    text = ModelConfig(name="chat", base_url="https://chat.example.com/v1", api_key="chat-token")
    image = ModelConfig(
        name="painter", provider="openai_images", base_url="https://image.example.com/v1", api_key="image-token"
    )
    mocker.patch.object(plugin_config, "models", [text, image])
    await set_available_model_names(SESSION, ["chat", "painter"])
    mocker.patch("src.plugins.llm.dialogue.send_reaction")
    send = mocker.patch.object(UniMessage, "send", autospec=True)
    tool_calls = [
        {
            "id": f"call_{index}",
            "type": "function",
            "function": {"name": "generate_image", "arguments": '{"prompt":"画猫"}'},
        }
        for index in range(2)
    ]
    chat = respx_mock.post("https://chat.example.com/v1/chat/completions").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "model": "chat",
                    "choices": [{"message": {"tool_calls": tool_calls}}],
                    "usage": {"prompt_tokens": 2, "completion_tokens": 3},
                },
            ),
            httpx.Response(500, json={"error": {"message": "summary unavailable"}}),
        ]
    )
    painter = respx_mock.post("https://image.example.com/v1/images/generations").mock(return_value=image_response(PNG))

    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter))
        ctx.receive_event(
            bot, fake_group_message_event_v11(message=Message("/chat -i --image-model painter 画猫"), user_id=10)
        )

    assert painter.call_count == 1
    assert painter.calls.last.request.headers["Authorization"] == "Bearer image-token"
    assert chat.call_count == 2
    assert chat.calls.last.request.headers["Authorization"] == "Bearer chat-token"
    tool_outputs = [
        m["content"] for m in json.loads(chat.calls.last.request.content)["messages"] if m["role"] == "tool"
    ]
    assert len(tool_outputs) == 2
    assert "本轮绘图次数已用完" in tool_outputs[1]
    assert send.await_args_list[0].args[0].get(Image)[0].raw == PNG
    assert "生图模型：painter" in send.await_args_list[1].args[0].extract_plain_text()
    assert "输入 7" in send.await_args_list[1].args[0].extract_plain_text()
    summary = send.await_args_list[2].args[0].extract_plain_text()
    assert "文字回复失败" in summary
    assert "输入 2" in summary
    assert "输入 9" not in summary


@pytest.mark.parametrize("command", ["/draw --hd --format png 画猫", "/draw 给你自己画一张高清魔理沙简笔头像"])
async def test_hd_requests_and_verifies_fixed_pixels(app: App, mocker, respx_mock: MockRouter, command):
    from nonebot_plugin_alconna import Image, UniMessage

    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names

    model = ModelConfig(
        name="painter",
        provider="openai_images",
        base_url="https://image.example.com/v1",
        image_sizes={"2880x2880"},
        extra_body={"output_format": "png", "quality": "high"},
    )
    mocker.patch.object(plugin_config, "models", [model])
    mocker.patch("src.plugins.llm.dialogue.send_reaction")
    send = mocker.patch.object(UniMessage, "send", autospec=True)
    await set_available_model_names(SESSION, ["painter"])
    png = make_image("PNG", size=(2880, 2880))
    route = respx_mock.post("https://image.example.com/v1/images/generations").mock(return_value=image_response(png))

    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter))
        ctx.receive_event(bot, fake_group_message_event_v11(message=Message(command), user_id=10))

    assert route.call_count == 1
    assert json.loads(route.calls.last.request.content)["size"] == "2880x2880"
    assert send.await_args_list[0].args[0].get(Image)[0].raw == png
    assert "PNG 2880x2880" in send.await_args_list[1].args[0].extract_plain_text()


@pytest.mark.parametrize(
    ("command", "output_format", "size", "extra", "formats", "sizes_by_format"),
    [
        ("/draw --hd --format png 画一个圆", "png", (2880, 2880), {}, set(), {}),
        ("/chat -d 画一张16:9的PNG横幅", "png", (1824, 1024), {}, set(), {}),
        ("/draw 画一张16:9的高清PNG横幅", "png", (3840, 2160), {}, set(), {}),
        *[
            (
                command,
                "gif",
                size,
                {"size": "auto", "output_format": "png", "frame_count": 2, "frame_duration_ms": 500},
                {"gif", "png"},
                {"gif": {"960x960", "1024x576"}},
            )
            for command, size in (
                ("/chat -d 画一张 16:9 的动图", (1024, 576)),
                ("/draw 生成一个 GIF 头像", (960, 960)),
            )
        ],
        (
            "/draw 画一张256像素见方的GIF贴纸",
            "gif",
            (256, 256),
            {"frame_count": 2},
            {"gif"},
            {"gif": {"256x256"}},
        ),
        (
            "/draw 画一张动态头像",
            "gif",
            (960, 960),
            {"output_format": "png", "size": "2880x2880", "frame_count": 2, "frame_duration_ms": 500},
            {"gif", "png"},
            {"gif": {"960x960"}, "png": {"2880x2880"}},
        ),
    ],
)
async def test_official_image_dimensions_send_the_calibrated_request(
    app: App,
    mocker,
    respx_mock: MockRouter,
    command,
    output_format,
    size,
    extra,
    formats,
    sizes_by_format,
):
    from nonebot_plugin_alconna import Image, UniMessage

    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names

    model = ModelConfig(
        name="official",
        model="gpt-image-2.6-sunburst",
        provider="openai_images",
        base_url="https://api.openai.com/v1",
        extra_body=extra,
        image_output_formats=formats,
        image_sizes_by_format=sizes_by_format,
    )
    mocker.patch.object(plugin_config, "models", [model])
    mocker.patch("src.plugins.llm.dialogue.send_reaction")
    send = mocker.patch.object(UniMessage, "send", autospec=True)
    await set_available_model_names(SESSION, [model.name])
    image = make_image(output_format.upper(), size=size, frames=2 if output_format == "gif" else 1)
    route = respx_mock.post("https://api.openai.com/v1/images/generations").mock(return_value=image_response(image))

    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter))
        ctx.receive_event(bot, fake_group_message_event_v11(message=Message(command), user_id=10))

    pixels = f"{size[0]}x{size[1]}"
    assert route.call_count == 1
    payload = json.loads(route.calls.last.request.content)
    assert payload["size"] == pixels
    assert payload["output_format"] == output_format
    if output_format == "gif":
        assert payload["frame_count"] == 2
    assert send.await_args_list[0].args[0].get(Image)[0].raw == image
    assert f"{output_format.upper()} {pixels}" in send.await_args_list[1].args[0].extract_plain_text()


@pytest.mark.parametrize(
    ("command", "requested", "returned", "expected_error"),
    [
        (
            "/draw --format gif --size 3200x1440 画个动画",
            "3200x1440",
            None,
            "frame sheet exceeds current request pixel budget",
        ),
        ("/draw 画一张128像素见方的GIF", "128x128", (128, 128), ""),
        ("/draw --format gif --size auto 画个动画", "auto", (256, 256), ""),
        ("/draw 画一张16:9的动态壁纸", "1024x576", (1024, 576), ""),
        ("/draw 画一张 GIF 头像", "960x960", (960, 960), ""),
    ],
)
async def test_official_gif_presets_do_not_limit_explicit_sizes(
    app: App,
    mocker,
    respx_mock: MockRouter,
    command,
    requested,
    returned,
    expected_error,
):
    from nonebot_plugin_alconna import Image, UniMessage

    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names

    model = ModelConfig(
        name="official",
        model="gpt-image-2.6-sunburst",
        provider="openai_images",
        base_url="https://api.openai.com/v1",
        image_output_formats={"gif"},
        image_gif_size_presets={"960x960", "1024x576"},
        extra_body={"size": "auto", "frame_count": 2, "frame_duration_ms": 500},
    )
    mocker.patch.object(plugin_config, "models", [model])
    mocker.patch("src.plugins.llm.dialogue.send_reaction")
    await set_available_model_names(SESSION, [model.name])
    gif = make_image("GIF", size=returned, frames=2) if returned else None
    if gif:
        send = mocker.patch.object(UniMessage, "send", autospec=True)
    reply = image_response(gif) if gif else httpx.Response(400, json={"error": {"message": expected_error}})
    route = respx_mock.post("https://api.openai.com/v1/images/generations").mock(return_value=reply)

    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter))
        event = fake_group_message_event_v11(message=Message(command), user_id=10)
        ctx.receive_event(bot, event)
        if expected_error:
            ctx.should_call_send(event, f"绘图失败：{expected_error}", True, at_sender=True)

    assert route.call_count == 1
    payload = json.loads(route.calls.last.request.content)
    assert (payload["size"], payload["output_format"], payload["frame_count"]) == (requested, "gif", 2)
    if gif:
        assert send.await_args_list[0].args[0].get(Image)[0].raw == gif
        assert f"GIF {returned[0]}x{returned[1]}" in send.await_args_list[1].args[0].extract_plain_text()


@pytest.mark.parametrize(
    ("command", "request_size", "requested_frames", "response_size", "response_frames", "error"),
    [
        ("/draw 画一张高清 GIF 头像", "auto", None, (1152, 1152), 9, ""),
        ("/draw --format gif --hd --frames 12 画头像", "auto", 12, (1152, 1152), 12, ""),
        ("/chat -d 画一张12帧的16:9高清GIF", "auto", 12, (1024, 576), 12, ""),
        ("/draw --frames 16 --size 320x320 画动图", "320x320", 16, (320, 320), 16, ""),
        ("/draw 画一张16:9的高清动图", "auto", None, (960, 960), 9, "第 1 张图片要求宽高比 16:9，服务返回 960x960"),
        ("/draw --frames 12 --size auto 画动图", "auto", 12, (512, 512), 9, "第 1 张图片要求 12 帧 GIF，服务返回 9 帧"),
        ("/draw 画一张17帧的GIF", None, None, None, 0, "官方 GIF 帧数必须是 2 至 16 之间的整数"),
        ("/draw --frames 1 画动图", None, None, None, 0, "官方 GIF 帧数必须是 2 至 16 之间的整数"),
        ("/draw --frames 8 --format png 画头像", None, None, None, 0, "--frames 仅适用于 GIF"),
    ],
)
async def test_official_gif_hd_and_frame_count_are_independent(
    app: App,
    mocker,
    respx_mock: MockRouter,
    command,
    request_size,
    requested_frames,
    response_size,
    response_frames,
    error,
):
    from nonebot_plugin_alconna import Image, UniMessage

    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names

    model = ModelConfig(
        name="official",
        model="gpt-image-2.6-sunburst",
        provider="openai_images",
        base_url="https://api.openai.com/v1",
        image_output_formats={"gif", "png"},
        image_gif_size_presets={"960x960", "1024x576"},
        extra_body={"size": "auto", "output_format": "png"},
    )
    mocker.patch.object(plugin_config, "models", [model])
    mocker.patch("src.plugins.llm.dialogue.send_reaction")
    await set_available_model_names(SESSION, [model.name])
    route = None
    if response_size:
        image = make_image("GIF", size=response_size, frames=response_frames)
        route = respx_mock.post("https://api.openai.com/v1/images/generations").mock(return_value=image_response(image))
    if not error:
        send = mocker.patch.object(UniMessage, "send", autospec=True)

    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter))
        event = fake_group_message_event_v11(message=Message(command), user_id=10)
        ctx.receive_event(bot, event)
        if error:
            ctx.should_call_send(event, ("绘图失败：" if route else "") + error, True, at_sender=True)
    if route is None:
        assert not respx_mock.calls
        return
    assert route.call_count == 1
    payload = json.loads(route.calls.last.request.content)
    assert payload["size"] == request_size
    assert payload["output_format"] == "gif"
    assert payload.get("frame_count") == requested_frames
    if not error:
        assert send.await_args_list[0].args[0].get(Image)[0].raw == image
        assert f"/ {response_frames} 帧" in send.await_args_list[1].args[0].extract_plain_text()


@pytest.mark.parametrize(
    ("description", "formats", "sizes_by_format", "error"),
    [
        ("画一张4096x4096 PNG", set(), {}, "要求 PNG / 4096x4096；official：官方 Images 单边最多 3840 像素"),
        ("画一张1820x1024 PNG", set(), {}, "要求 PNG / 1820x1024；official：官方 Images 宽高都必须是 16 的倍数"),
        (
            "画一张3200x3200 PNG",
            set(),
            {},
            "要求 PNG / 3200x3200；official：官方 Images 总像素必须在 655360 至 8294400 之间",
        ),
        ("画一张960方形的GIF", set(), {}, "要求 GIF / 960x960；official：未声明支持 gif 格式"),
        (
            "画一张1024方形的GIF",
            {"gif", "png"},
            {"gif": {"960x960"}, "png": {"1024x1024"}},
            "要求 GIF / 1024x1024；official：gif 未声明支持 1024x1024，已配置尺寸：960x960",
        ),
    ],
)
async def test_official_invalid_image_requirements_are_rejected_before_network(
    app: App,
    mocker,
    respx_mock: MockRouter,
    description,
    formats,
    sizes_by_format,
    error,
):
    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names

    model = ModelConfig(
        name="official",
        model="gpt-image-2.6-flare",
        provider="openai_images",
        base_url="https://api.openai.com/v1",
        image_output_formats=formats,
        image_sizes_by_format=sizes_by_format,
    )
    mocker.patch.object(plugin_config, "models", [model])
    await set_available_model_names(SESSION, [model.name])

    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter))
        event = fake_group_message_event_v11(message=Message(f"/draw {description}"), user_id=10)
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, f"本群没有满足绘图要求的模型（{error}）", True, at_sender=True)

    assert not respx_mock.calls


@pytest.mark.parametrize("command", ["/draw", "/chat -d"])
async def test_official_draw_edits_a_replied_image(app: App, mocker, respx_mock: MockRouter, command: str):
    from nonebot.adapters.onebot.v11.event import Reply, Sender
    from nonebot_plugin_alconna import Image, UniMessage

    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names

    model = ModelConfig(
        name="official",
        model="gpt-image-2.6-sunburst",
        provider="openai_images",
        base_url="https://api.openai.com/v1",
        api_key="edit-test",
        extra_body={"quality": "low", "n": 1},
    )
    mocker.patch.object(plugin_config, "models", [model])
    mocker.patch("src.plugins.llm.dialogue.send_reaction")
    send = mocker.patch.object(UniMessage, "send", autospec=True)
    reference = make_image("JPEG")
    output = make_image("PNG", size=(1024, 1024))
    mocker.patch("src.plugins.llm.content.image_fetch", return_value=reference)
    await set_available_model_names(SESSION, [model.name])
    edit = respx_mock.post("https://api.openai.com/v1/images/edits").mock(return_value=image_response(output))
    generate = respx_mock.post("https://api.openai.com/v1/images/generations").mock(return_value=image_response(output))
    previous = Reply(
        time=1,
        message_type="group",
        message_id=9211,
        real_id=9211,
        sender=Sender(user_id=20, nickname="群友"),
        message=Message("保留构图[CQ:image,file=ref.jpg]"),
    )
    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter), self_id="123456")
        ctx.receive_event(
            bot,
            fake_group_message_event_v11(
                self_id=123456,
                message_id=2711 if command == "/draw" else 2712,
                user_id=10,
                reply=previous,
                message=Message(f"{command} --format png --size 1024x1024 把主角改成红色"),
            ),
        )

    assert edit.call_count == 1
    assert generate.call_count == 0
    request = edit.calls.last.request
    assert request.headers["authorization"] == "Bearer edit-test"
    assert request.headers["content-type"].startswith("multipart/form-data; boundary=")
    from email import policy
    from email.parser import BytesParser

    parts = BytesParser(policy=policy.default).parsebytes(
        f"Content-Type: {request.headers['content-type']}\r\n\r\n".encode() + request.content
    )
    fields = {part.get_param("name", header="content-disposition"): part for part in parts.iter_parts()}
    assert fields["image[]"].get_payload(decode=True) == reference
    assert fields["image[]"].get_content_type() == "image/jpeg"
    assert b"1024x1024" in fields["size"].get_payload(decode=True)
    assert b"png" in fields["output_format"].get_payload(decode=True)
    assert "把主角改成红色".encode() in fields["prompt"].get_payload(decode=True)
    assert send.await_args_list[0].args[0].get(Image)[0].raw == output


async def test_deliver_before_disclosing_no_responses_continuation(app: App, mocker, respx_mock: MockRouter):
    from nonebot_plugin_alconna import Image, UniMessage

    from src.plugins.llm.config import ModelConfig, plugin_config
    from src.plugins.llm.data_source import set_available_model_names

    model = ModelConfig(
        name="painter",
        provider="openai_responses",
        base_url="https://image.example.com/v1",
        capabilities={"image_generation"},
    )
    mocker.patch.object(plugin_config, "models", [model])
    mocker.patch("src.plugins.llm.dialogue.send_reaction")
    send = mocker.patch.object(UniMessage, "send", autospec=True)
    wait = mocker.patch("nonebot_plugin_waiter.prompt")
    await set_available_model_names(SESSION, ["painter"])
    route = respx_mock.post("https://image.example.com/v1/responses").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {"type": "image_generation_call", "result": base64.b64encode(PNG).decode()},
                ],
            },
        )
    )

    async with app.test_matcher() as ctx:
        bot = ctx.create_bot(base=Bot, adapter=get_adapter(Adapter))
        event = fake_group_message_event_v11(message=Message("/draw -c 画猫"), user_id=10)
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "生图服务没有返回可续画的图片记录；已停止多轮绘图", True)

    assert route.call_count == 1
    assert send.await_args_list[0].args[0].get(Image)[0].raw == PNG
    assert "服务未返回用量" in send.await_args_list[1].args[0].extract_plain_text()
    wait.assert_not_awaited()
