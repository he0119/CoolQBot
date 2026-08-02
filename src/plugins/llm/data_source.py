"""群组大模型配置的读写"""

from nonebot_plugin_orm import get_session
from sqlalchemy import select

from .config import plugin_config
from .models import GroupLLMConfig


async def _get_config(session_id: str) -> GroupLLMConfig | None:
    async with get_session() as session:
        return (
            await session.scalars(select(GroupLLMConfig).where(GroupLLMConfig.session_id == session_id))
        ).one_or_none()


async def get_model_name(session_id: str) -> str:
    """获取群组当前使用的模型名

    群组未设置或所设模型已下线时，回退到配置中的第一个模型。
    """
    names = plugin_config.get_model_names()
    if not names:
        raise ValueError("未配置任何模型，请先在 .env 中配置 LLM__MODELS")

    config = await _get_config(session_id)
    if config and config.model_name in names:
        return config.model_name
    return names[0]


async def set_model_name(session_id: str, model_name: str) -> None:
    """设置群组默认模型"""
    async with get_session() as session:
        config = (
            await session.scalars(select(GroupLLMConfig).where(GroupLLMConfig.session_id == session_id))
        ).one_or_none()
        if config:
            config.model_name = model_name
        else:
            session.add(GroupLLMConfig(session_id=session_id, model_name=model_name))
        await session.commit()


async def get_tts_model(session_id: str) -> str:
    """获取群组当前使用的 TTS 模型名"""
    config = await _get_config(session_id)
    if config and config.tts_model:
        return config.tts_model
    return plugin_config.tts_model


async def set_tts_model(session_id: str, tts_model: str) -> None:
    """设置群组默认 TTS 模型"""
    async with get_session() as session:
        config = (
            await session.scalars(select(GroupLLMConfig).where(GroupLLMConfig.session_id == session_id))
        ).one_or_none()
        if config:
            config.tts_model = tts_model
        else:
            session.add(GroupLLMConfig(session_id=session_id, tts_model=tts_model))
        await session.commit()
