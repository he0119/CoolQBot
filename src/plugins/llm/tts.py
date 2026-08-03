"""TTS 语音合成

对接 GPT-SoVITS 推理服务：先请求 `/infer_single` 得到音频地址，再下载音频数据。
"""

from __future__ import annotations

from time import perf_counter

import httpx
from nonebot.log import logger

from .config import plugin_config


class TTSError(Exception):
    """语音合成失败"""


async def get_tts_models() -> list[str]:
    """获取可用的 TTS 模型列表"""
    if not plugin_config.tts_enabled:
        raise TTSError("当前未启用 TTS 功能")

    started_at = perf_counter()
    logger.info("TTS 模型列表查询开始")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{plugin_config.tts_base_url.rstrip('/')}/models",
                json={"version": "v4"},
                timeout=plugin_config.tts_timeout,
            )
            response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning(
            "TTS 模型列表查询失败（错误类型={}，耗时={:.3f}s）",
            type(e).__name__,
            perf_counter() - started_at,
        )
        raise TTSError(f"获取 TTS 模型列表失败：{e}") from e

    models = response.json().get("models") or {}
    result = sorted(models)
    logger.info("TTS 模型列表查询完成（模型数量={}，耗时={:.3f}s）", len(result), perf_counter() - started_at)
    return result


async def text_to_speech(text: str, model: str) -> bytes:
    """把文本合成为语音，返回音频数据"""
    if not plugin_config.tts_enabled:
        raise TTSError("当前未启用 TTS 功能")
    if not model:
        raise TTSError("未设置 TTS 模型，请先使用 /llm tts --set 设置")

    base_url = plugin_config.tts_base_url.rstrip("/")
    started_at = perf_counter()
    logger.info("TTS 合成开始（模型={}，文本字符={}）", model, len(text))
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
    except TTSError:
        logger.warning(
            "TTS 合成失败（模型={}，原因=服务未返回音频地址，耗时={:.3f}s）", model, perf_counter() - started_at
        )
        raise
    except httpx.HTTPError as e:
        logger.warning(
            "TTS 合成失败（模型={}，错误类型={}，耗时={:.3f}s）",
            model,
            type(e).__name__,
            perf_counter() - started_at,
        )
        raise TTSError(f"连接 TTS 服务失败：{e}") from e

    logger.info(
        "TTS 合成完成（模型={}，音频字节={}，耗时={:.3f}s）", model, len(audio.content), perf_counter() - started_at
    )
    return audio.content
