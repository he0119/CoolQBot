"""TTS 语音合成

对接 GPT-SoVITS 推理服务：先请求 `/infer_single` 得到音频地址，再下载音频数据。
"""

from __future__ import annotations

import httpx

from .config import plugin_config


class TTSError(Exception):
    """语音合成失败"""


async def get_tts_models() -> list[str]:
    """获取可用的 TTS 模型列表"""
    if not plugin_config.tts_enabled:
        raise TTSError("当前未启用 TTS 功能")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{plugin_config.tts_base_url.rstrip('/')}/models",
                json={"version": "v4"},
                timeout=plugin_config.tts_timeout,
            )
            response.raise_for_status()
    except httpx.HTTPError as e:
        raise TTSError(f"获取 TTS 模型列表失败：{e}") from e

    models = response.json().get("models") or {}
    return sorted(models)


async def text_to_speech(text: str, model: str) -> bytes:
    """把文本合成为语音，返回音频数据"""
    if not plugin_config.tts_enabled:
        raise TTSError("当前未启用 TTS 功能")
    if not model:
        raise TTSError("未设置 TTS 模型，请先使用 /llm tts --set 设置")

    base_url = plugin_config.tts_base_url.rstrip("/")
    payload = {
        "text": text,
        "model_name": model,
        "app_key": plugin_config.tts_access_token,
        "access_token": plugin_config.tts_access_token,
        "version": "v4",
        "text_lang": "多语种混合",
        "prompt_text_lang": "中文",
        "media_type": "wav",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/infer_single",
                headers={"Authorization": f"Bearer {plugin_config.tts_access_token}"},
                json=payload,
                timeout=plugin_config.tts_timeout,
            )
            response.raise_for_status()

            audio_url = response.json().get("audio_url")
            if not audio_url:
                raise TTSError("语音合成失败，服务未返回音频地址")

            audio = await client.get(audio_url, timeout=plugin_config.tts_timeout)
            audio.raise_for_status()
    except httpx.HTTPError as e:
        raise TTSError(f"连接 TTS 服务失败：{e}") from e

    return audio.content
