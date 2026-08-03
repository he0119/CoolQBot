"""测试 LLM 语音合成"""

import pytest
from nonebug import App


async def test_text_to_speech_without_model_shows_valid_command(app: App, mocker):
    """未设置模型时提示可直接使用的设置命令"""
    from src.plugins.llm.config import plugin_config
    from src.plugins.llm.tts import TTSError, text_to_speech

    mocker.patch.object(plugin_config, "tts_base_url", "https://tts.example.com")

    with pytest.raises(TTSError, match=r"/llm tts --set"):
        await text_to_speech("你好", "")
