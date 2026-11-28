"""用模拟服务检查绘图接口的能力、请求参数和结果。"""

import base64
import json
from copy import deepcopy

import httpx
import pytest

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 16
ENCODED_PNG = base64.b64encode(PNG).decode()
OFFICIAL_URL = "https://api.openai.com/v1"
GATEWAY_URL = "https://gateway.example"
IMAGE_TOOL = {"type": "image_generation"}
WEB_TOOL = {"type": "web_search"}


@pytest.mark.parametrize("model_id", ["gpt-image-2.5-sunburst", "gpt-image-2.5-flare-2026-09-08"])
async def test_official_static_model_edits_references(app, respx_mock, model_id):
    from src.plugins.llm.config import ModelConfig
    from src.plugins.llm.providers import (
        ImageRequestOptions,
        generate_images,
        get_image_capabilities,
        image_options_error,
    )
    from src.plugins.llm.schemas import ImageContent

    extra_body = {
        "size": "1024x1024",
        "output_format": "jpeg",
        "quality": "high",
        "moderation": "low",
        "frame_count": 9,
    }
    model = ModelConfig(
        name="painter", model=model_id, provider="openai_images", base_url=OFFICIAL_URL, extra_body=extra_body
    )
    caps = get_image_capabilities(model)
    assert caps.references
    assert caps.official_geometry
    assert caps.auto_size
    assert not caps.continuation
    assert not caps.gif
    assert not caps.explicit_frames
    assert caps.defaults == ImageRequestOptions("jpeg", "1024x1024")
    assert "不支持动态 GIF" in image_options_error(model, ImageRequestOptions(output_format="gif"))
    assert "16 的倍数" in image_options_error(model, ImageRequestOptions(size="1535x1024"))
    route = respx_mock.post(f"{OFFICIAL_URL}/images/edits").mock(
        return_value=httpx.Response(
            200,
            json={"data": [{"b64_json": ENCODED_PNG}], "usage": {"input_tokens": 3, "output_tokens": 5}},
        )
    )

    result = await generate_images(
        model,
        "改成红色",
        options=ImageRequestOptions("png", "1536x1024"),
        session_affinity="image-session",
        images=[ImageContent.from_bytes(PNG)],
    )

    request = route.calls.last.request
    assert request.headers["x-session-affinity"] == "image-session"
    assert request.headers["content-type"].startswith("multipart/form-data;")
    assert b'name="image[]"; filename="reference-1.png"' in request.content
    assert b'name="size"\r\n\r\n1536x1024' in request.content
    assert b'name="output_format"\r\n\r\npng' in request.content
    assert b'name="quality"\r\n\r\nhigh' in request.content
    assert b'name="moderation"\r\n\r\nlow' in request.content
    assert b"frame_count" not in request.content
    assert [image.data for image in result.images] == [PNG]
    assert result.usage is not None
    assert result.usage.output_tokens == 5
    assert model.extra_body == extra_body


@pytest.mark.parametrize(
    ("extra", "error"),
    [
        ({"frame_count": 1}, "2 至 16"),
        ({"frame_count": True}, "2 至 16"),
        ({"frame_duration_ms": 2001}, "20 至 2000"),
        ({"stream": True}, "不支持流式"),
        ({"partial_images": 1}, "不支持流式"),
        ({"output_compression": 0}, "不支持流式"),
        ({"size": "4096x1536"}, "单边最多 3840"),
    ],
)
async def test_official_gif_rejects_invalid_configured_defaults(app, respx_mock, extra, error):
    from src.plugins.llm.config import ModelConfig
    from src.plugins.llm.providers import ImageRequestOptions, ProviderError, generate_images, image_options_error

    model = ModelConfig(
        name="animation",
        model="gpt-image-2.6-flare",
        provider="openai_images",
        base_url=OFFICIAL_URL,
        extra_body={"output_format": "gif", **extra},
    )

    assert error in image_options_error(model, ImageRequestOptions())
    with pytest.raises(ProviderError, match=error):
        await generate_images(model, "画一个动画")
    assert not respx_mock.calls


async def test_official_gif_overrides_only_requested_fields(app, respx_mock):
    from src.plugins.llm.config import ModelConfig
    from src.plugins.llm.providers import ImageRequestOptions, generate_images, get_image_capabilities

    extra_body = {"size": "320x320", "frame_count": 9, "frame_duration_ms": 500, "quality": "high"}
    model = ModelConfig(
        name="animation",
        model="gpt-image-2.6-sunburst",
        provider="openai_images",
        base_url=OFFICIAL_URL,
        image_output_formats={"gif", "png"},
        extra_body=extra_body,
    )
    caps = get_image_capabilities(model)
    assert caps.gif
    assert caps.explicit_frames
    assert caps.defaults == ImageRequestOptions(size="320x320", frame_count=9)
    route = respx_mock.post(f"{OFFICIAL_URL}/images/generations").mock(
        return_value=httpx.Response(
            200, json={"data": [{"b64_json": base64.b64encode(b"GIF89a" + b"0" * 16).decode()}]}
        )
    )

    await generate_images(model, "做一张动图", options=ImageRequestOptions(output_format="gif", frame_count=12))

    assert json.loads(route.calls.last.request.content) == {
        **extra_body,
        "model": model.model,
        "prompt": "做一张动图",
        "frame_count": 12,
        "output_format": "gif",
    }


async def test_gateway_keeps_declared_gif_and_private_fields(app, respx_mock):
    from src.plugins.llm.config import ModelConfig
    from src.plugins.llm.providers import (
        ImageRequestOptions,
        ProviderError,
        generate_images,
        get_image_capabilities,
        image_options_error,
    )
    from src.plugins.llm.schemas import ImageContent

    extra_body = {"size": "auto", "frame_count": 5, "vendor_settings": {"fast": True}}
    model = ModelConfig(
        name="gateway",
        model="gpt-image-2.6-flare",
        provider="openai_images",
        base_url=GATEWAY_URL,
        image_output_formats={"gif"},
        image_sizes_by_format={"gif": {"500x300"}},
        extra_body=extra_body,
    )
    caps = get_image_capabilities(model)
    assert caps.gif
    assert not caps.explicit_frames
    assert not caps.references
    assert not caps.official_geometry
    assert "未声明支持 320x320" in image_options_error(model, ImageRequestOptions("gif", "320x320"))
    assert "仅支持官方" in image_options_error(model, ImageRequestOptions("gif", "500x300", 8))
    with pytest.raises(ProviderError, match="不能使用参考图"):
        await generate_images(model, "改色", images=[ImageContent.from_bytes(PNG)])
    assert not respx_mock.calls
    route = respx_mock.post(f"{GATEWAY_URL}/images/generations").mock(
        return_value=httpx.Response(
            200, json={"data": [{"b64_json": base64.b64encode(b"GIF89a" + b"0" * 16).decode()}]}
        )
    )

    result = await generate_images(model, "画动图", options=ImageRequestOptions("gif", "500x300"))

    assert json.loads(route.calls.last.request.content) == {
        **extra_body,
        "size": "500x300",
        "output_format": "gif",
        "model": model.model,
        "prompt": "画动图",
    }
    assert result.usage is None


@pytest.mark.parametrize(("background", "tool_background"), [(True, "transparent"), ("opaque", "opaque")])
async def test_responses_drawing_builds_native_image_tool_and_preserves_usage(
    app, respx_mock, background, tool_background
):
    from src.plugins.llm.config import ModelConfig
    from src.plugins.llm.providers import ImageRequestOptions, generate_images, get_image_capabilities
    from src.plugins.llm.schemas import ImageContent, Message

    image_options = {
        "model": "gpt-image-2.5-sunburst",
        "background": "transparent",
        "size": "1024x1024",
        "quality": "high",
        "action": "edit",
        "partial_images": 1,
        "input_image_mask": {"file_id": "mask_1"},
    }
    model = ModelConfig(
        name="assistant",
        provider="openai_responses",
        base_url=OFFICIAL_URL,
        capabilities={"text", "vision", "image_generation"},
        extra_body={
            "model": "ignored-top-level-model",
            "input": "ignored-input",
            "background": background,
            "store": True,
            "tools": [WEB_TOOL, {**IMAGE_TOOL, **image_options, "frame_count": 7}],
            "quality": "medium",
            "output_format": "webp",
            "stream": True,
            "frame_duration_ms": 500,
            "tool_choice": "none",
            "reasoning": {"effort": "low"},
        },
    )
    original = deepcopy(model.extra_body)
    caps = get_image_capabilities(model)
    assert caps.references
    assert caps.continuation
    assert not caps.gif
    assert caps.defaults == ImageRequestOptions("webp", "1024x1024")
    prior_image = {"type": "image_generation_call", "id": "ig_1", "result": ENCODED_PNG}
    new_image = {**prior_image, "id": "ig_2"}
    route = respx_mock.post(f"{OFFICIAL_URL}/responses").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [{"type": "web_search_call", "id": "ws_1"}, new_image],
                "usage": {"input_tokens": 8, "output_tokens": 11, "input_tokens_details": {"cached_tokens": 2}},
            },
        )
    )

    result = await generate_images(
        model,
        "换色",
        options=ImageRequestOptions("png", "1536x864"),
        images=[ImageContent.from_bytes(PNG)],
        history=(Message.user("画山"), Message.assistant(provider_data={"responses_output": [prior_image]})),
    )

    payload = json.loads(route.calls.last.request.content)
    assert payload["model"] == model.model
    if isinstance(background, bool):
        assert payload["background"] is background
    else:
        assert "background" not in payload
    assert payload["store"] is True
    assert payload["stream"] is False
    assert payload["reasoning"] == {"effort": "low"}
    assert payload["tools"] == [
        WEB_TOOL,
        {
            **IMAGE_TOOL,
            **image_options,
            "background": tool_background,
            "quality": "medium",
            "output_format": "png",
            "size": "1536x864",
        },
    ]
    assert payload["tool_choice"] == IMAGE_TOOL
    assert not {"quality", "output_format", "frame_duration_ms"} & payload.keys()
    assert payload["input"][1] == prior_image
    assert [item["type"] for item in payload["input"][2]["content"]] == ["input_text", "input_image"]
    assert result.continuation is not None
    assert result.continuation.provider_data == {"responses_output": [new_image]}
    assert result.usage is not None
    assert result.usage.cache_read_tokens == 2
    assert model.extra_body == original


@pytest.mark.parametrize(
    ("other_tools", "choice", "expected"),
    [
        ([], IMAGE_TOOL, None),
        ([], "required", None),
        ([WEB_TOOL], "required", "required"),
        ([WEB_TOOL], {"type": "allowed_tools", "mode": "auto", "tools": [IMAGE_TOOL]}, None),
        (
            [WEB_TOOL],
            {"type": "allowed_tools", "mode": "required", "tools": [IMAGE_TOOL, WEB_TOOL]},
            {"type": "allowed_tools", "mode": "required", "tools": [WEB_TOOL]},
        ),
    ],
)
@pytest.mark.parametrize("background", [True, False, "opaque"])
def test_prepare_chat_model_removes_only_image_settings(app, other_tools, choice, expected, background):
    from src.plugins.llm.config import ModelConfig
    from src.plugins.llm.providers import ResponsesProvider, prepare_chat_model
    from src.plugins.llm.schemas import Message

    model = ModelConfig(
        name="assistant",
        provider="openai_responses",
        base_url=GATEWAY_URL,
        extra_body={
            "tools": [{**IMAGE_TOOL, "background": "transparent"}, *other_tools],
            "tool_choice": choice,
            "background": background,
            "output_format": "png",
            "size": "1024x1024",
            "frame_count": 7,
            "reasoning": {"effort": "low"},
        },
    )
    before = deepcopy(model.extra_body)

    prepared = prepare_chat_model(model)
    payload = ResponsesProvider(prepared).build_payload([Message.user("你好")])

    assert payload.get("tools", []) == other_tools
    assert payload.get("tool_choice") == expected
    assert payload.get("background") is (background if isinstance(background, bool) else None)
    assert not {"output_format", "size", "frame_count"} & payload.keys()
    prepared.extra_body["reasoning"]["effort"] = "high"
    assert model.extra_body == before


@pytest.mark.parametrize("output", [[], [{"type": "image_generation_call", "result": "@@@"}]])
async def test_responses_preserves_reported_usage_for_undeliverable_images(app, respx_mock, output):
    from src.plugins.llm.config import ModelConfig
    from src.plugins.llm.providers import ImageResponseError, generate_images

    model = ModelConfig(
        name="assistant", provider="openai_responses", base_url=GATEWAY_URL, capabilities={"image_generation"}
    )
    respx_mock.post(f"{GATEWAY_URL}/responses").mock(
        return_value=httpx.Response(
            200, json={"status": "completed", "output": output, "usage": {"input_tokens": 0, "output_tokens": 0}}
        )
    )

    with pytest.raises(ImageResponseError) as error:
        await generate_images(model, "画山")

    assert error.value.usage is not None
    assert error.value.usage.output_tokens == 0
