"""大模型额度查询 API

注意：当前插件仅支持 Tailscale Aperture 格式的 API。
"""

import httpx
from nonebot_plugin_orm import get_session
from pydantic import BaseModel
from sqlalchemy import delete, select

from .models import GroupQuotaConfig


class Bucket(BaseModel):
    """额度桶"""

    name: str
    """桶名称"""
    current: int
    """当前剩余额度（单位：纳元，除以 1_000_000_000 为元）"""
    capacity: int
    """总容量（单位：纳元，除以 1_000_000_000 为元）"""
    rate: str
    """速率限制"""
    models: list[str]
    """关联的模型列表"""
    paused: bool
    """是否暂停"""
    last_updated: str
    """最后更新时间"""


class QuotasResponse(BaseModel):
    """额度查询响应"""

    buckets: list[Bucket]
    """额度桶列表"""


async def get_group_api_url(session_id: str) -> str | None:
    """获取群组配置的 API 地址"""
    async with get_session() as session:
        config = (
            await session.scalars(select(GroupQuotaConfig).where(GroupQuotaConfig.session_id == session_id))
        ).one_or_none()
        return config.api_url if config else None


async def set_group_api_url(session_id: str, api_url: str) -> None:
    """设置群组的 API 地址"""
    async with get_session() as session:
        config = (
            await session.scalars(select(GroupQuotaConfig).where(GroupQuotaConfig.session_id == session_id))
        ).one_or_none()
        if config:
            config.api_url = api_url
        else:
            session.add(GroupQuotaConfig(session_id=session_id, api_url=api_url))
        await session.commit()


async def remove_group_api_url(session_id: str) -> bool:
    """删除群组的 API 地址"""
    async with get_session() as session:
        result = await session.execute(delete(GroupQuotaConfig).where(GroupQuotaConfig.session_id == session_id))
        await session.commit()
        return result.rowcount > 0


async def get_quotas(api_url: str) -> str:
    """获取大模型额度信息"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(api_url, timeout=10.0)
            resp.raise_for_status()
            data = QuotasResponse.model_validate(resp.json())
    except httpx.HTTPError:
        return "获取额度信息失败，请稍后再试"

    if not data.buckets:
        return "未找到额度信息"

    lines = ["大模型剩余额度："]
    for bucket in data.buckets:
        remaining_yuan = bucket.current / 1_000_000_000
        lines.append(f"  {bucket.name}: {remaining_yuan:.2f} 元")

    return "\n".join(lines)
