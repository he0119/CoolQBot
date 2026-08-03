"""测试 LLM 语音合成"""

import httpx
import pytest
import respx
from nonebug import App
from respx import MockRouter


async def test_text_to_speech_without_model_shows_valid_command(app: App, mocker):
    """未设置模型时提示可直接使用的设置命令"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.tts import TTSError, text_to_speech

    mocker.patch.object(plugin_config, "tts_base_url", "https://tts.example.com")

    with pytest.raises(TTSError, match=r"/llm tts --set"):
        await text_to_speech("你好", "")


@respx.mock(assert_all_called=True)
async def test_text_to_speech_logs_metadata_without_content(app: App, respx_mock: MockRouter, mocker):
    """TTS 日志记录模型、长度和音频大小，不记录正文、令牌或音频 URL。"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.tts import text_to_speech

    mocker.patch.object(plugin_config, "tts_base_url", "https://tts.example.com")
    mocker.patch.object(plugin_config, "tts_access_token", "secret-token")
    logger_info = mocker.patch("src.plugins.llm.tts.logger.info")
    respx_mock.post("https://tts.example.com/infer_single").mock(
        return_value=httpx.Response(
            200,
            json={"audio_url": "https://cdn.example.com/audio.wav?token=private"},
        )
    )
    respx_mock.get("https://cdn.example.com/audio.wav?token=private").mock(
        return_value=httpx.Response(200, content=b"audio")
    )

    result = await text_to_speech("private-text", "voice-model")

    assert result == b"audio"
    log_text = " ".join(str(item) for item in logger_info.call_args_list)
    assert "voice-model" in log_text
    assert "private-text" not in log_text
    assert "secret-token" not in log_text
    assert "audio.wav" not in log_text
    assert "token=private" not in log_text
