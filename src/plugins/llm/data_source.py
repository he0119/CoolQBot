"""群组大模型配置的读写"""

from nonebot.log import logger
from nonebot_plugin_orm import get_session
from sqlalchemy import select, update

from .config import plugin_config
from .models import GroupLLMConfig


async def _get_config(session_id: str) -> GroupLLMConfig | None:
    async with get_session() as session:
        return (
            await session.scalars(select(GroupLLMConfig).where(GroupLLMConfig.session_id == session_id))
        ).one_or_none()


def _available_names(config: GroupLLMConfig | None) -> list[str]:
    """按全局配置顺序筛出本群可用模型。"""
    names = plugin_config.get_model_names()
    if not config or config.available_models is None:
        return []
    allowed = set(config.available_models)
    return [name for name in names if name in allowed]


async def get_available_model_names(session_id: str) -> list[str]:
    """获取本群可用模型；未配置准入列表时默认拒绝。"""
    return _available_names(await _get_config(session_id))


async def get_model_name(session_id: str) -> str:
    """获取群组当前使用的模型名

    群组未设置或所设模型已下线时，回退到本群开放的第一个模型。
    """
    if not plugin_config.get_model_names():
        raise ValueError("未配置任何模型，请先在 .env 中配置 LLM__MODELS")

    config = await _get_config(session_id)
    names = _available_names(config)
    if not names:
        raise ValueError("本群未开放任何模型，请联系超级管理员配置")
    if config and config.model_name in names:
        return config.model_name
    return names[0]


async def set_model_name(session_id: str, model_name: str) -> None:
    """设置群组默认模型"""
    if model_name not in await get_available_model_names(session_id):
        raise ValueError(f"本群未启用的模型：{model_name}")
    async with get_session() as session:
        config = (
            await session.scalars(select(GroupLLMConfig).where(GroupLLMConfig.session_id == session_id))
        ).one_or_none()
        if config:
            config.model_name = model_name
        else:
            session.add(GroupLLMConfig(session_id=session_id, model_name=model_name))
        await session.commit()
    logger.info("LLM 群组默认模型已更新（模型={}）", model_name)


async def set_available_model_names(session_id: str, model_names: list[str]) -> list[str]:
    """设置本群可用模型，并清理不再可用的群级模型选择。"""
    configured_names = plugin_config.get_model_names()
    requested = set(model_names)
    unknown = list(dict.fromkeys(name for name in model_names if name not in configured_names))
    if unknown:
        raise ValueError(f"未配置的模型：{'、'.join(unknown)}")
    available = [name for name in configured_names if name in requested]
    if not available:
        raise ValueError("至少需要为本群开放一个模型")

    for attempt in range(2):
        async with get_session() as session:
            config = (
                await session.scalars(select(GroupLLMConfig).where(GroupLLMConfig.session_id == session_id))
            ).one_or_none()
            if config:
                await session.execute(
                    update(GroupLLMConfig)
                    .where(GroupLLMConfig.session_id == session_id)
                    .values(
                        available_models=available,
                        model_name=config.model_name if config.model_name in available else available[0],
                        zssm_model=config.zssm_model if config.zssm_model in available else None,
                        zssm_vision_model=(config.zssm_vision_model if config.zssm_vision_model in available else None),
                    )
                )
            else:
                session.add(
                    GroupLLMConfig(
                        session_id=session_id,
                        available_models=available,
                        model_name=available[0],
                    )
                )
            await session.commit()

        persisted = await get_available_model_names(session_id)
        if persisted == available:
            logger.info("LLM 群组可用模型已更新（数量={}）", len(available))
            return persisted
        logger.warning("LLM 群组可用模型回读不一致（重试={}）", attempt == 0)

    raise ValueError("群组可用模型保存失败，请重试；若持续失败，请重启机器人并确认数据库迁移已应用")


async def clear_available_model_names(session_id: str) -> None:
    """清空本群模型准入列表。"""
    async with get_session() as session:
        config = (
            await session.scalars(select(GroupLLMConfig).where(GroupLLMConfig.session_id == session_id))
        ).one_or_none()
        if config:
            config.available_models = None
            config.model_name = None
            config.zssm_model = None
            config.zssm_vision_model = None
            await session.commit()
    logger.info("LLM 群组可用模型已清空")


async def get_zssm_model_name(session_id: str) -> str:
    """获取本群解释模型；未单独设置时跟随本群默认模型。"""
    config = await _get_config(session_id)
    names = _available_names(config)
    if config and config.zssm_model in names:
        return config.zssm_model
    return await get_model_name(session_id)


async def set_zssm_model_name(session_id: str, model_name: str) -> None:
    """设置本群解释模型。"""
    if model_name not in await get_available_model_names(session_id):
        raise ValueError(f"本群未启用的模型：{model_name}")
    async with get_session() as session:
        config = (
            await session.scalars(select(GroupLLMConfig).where(GroupLLMConfig.session_id == session_id))
        ).one_or_none()
        if config:
            config.zssm_model = model_name
        else:
            session.add(GroupLLMConfig(session_id=session_id, zssm_model=model_name))
        await session.commit()
    logger.info("LLM 群组解释模型已更新（模型={}）", model_name)


async def clear_zssm_model_name(session_id: str) -> None:
    """清除本群解释模型，使其跟随本群默认模型。"""
    async with get_session() as session:
        config = (
            await session.scalars(select(GroupLLMConfig).where(GroupLLMConfig.session_id == session_id))
        ).one_or_none()
        if config:
            config.zssm_model = None
            await session.commit()
    logger.info("LLM 群组解释模型已恢复为跟随默认模型")


async def get_zssm_vision_model_name(session_id: str) -> str:
    """获取本群解释模式使用的独立视觉模型。"""
    config = await _get_config(session_id)
    names = _available_names(config)
    if config and config.zssm_vision_model in names:
        return config.zssm_vision_model or ""
    return ""


async def set_zssm_vision_model_name(session_id: str, model_name: str) -> None:
    """设置本群解释模式使用的独立视觉模型。"""
    if model_name not in await get_available_model_names(session_id):
        raise ValueError(f"本群未启用的模型：{model_name}")
    if "vision" not in plugin_config.get_model(model_name).capabilities:
        raise ValueError(f"视觉模型 {model_name} 未声明 vision 能力")
    async with get_session() as session:
        config = (
            await session.scalars(select(GroupLLMConfig).where(GroupLLMConfig.session_id == session_id))
        ).one_or_none()
        if config:
            config.zssm_vision_model = model_name
        else:
            session.add(GroupLLMConfig(session_id=session_id, zssm_vision_model=model_name))
        await session.commit()
    logger.info("LLM 群组视觉模型已更新（模型={}）", model_name)


async def clear_zssm_vision_model_name(session_id: str) -> None:
    """清除本群解释模式使用的独立视觉模型。"""
    async with get_session() as session:
        config = (
            await session.scalars(select(GroupLLMConfig).where(GroupLLMConfig.session_id == session_id))
        ).one_or_none()
        if config:
            config.zssm_vision_model = None
            await session.commit()
    logger.info("LLM 群组视觉模型已清除")


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
    logger.info("LLM 群组默认 TTS 模型已更新（模型={}）", tts_model)
