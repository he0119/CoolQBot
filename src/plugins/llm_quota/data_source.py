"""大模型额度查询 API

注意：当前插件仅支持 Tailscale Aperture 格式的 API。
"""

import httpx

from .config import plugin_config


async def get_quotas() -> str:
    """获取大模型额度信息"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(plugin_config.llm_quota_api_url, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError:
        return "获取额度信息失败，请稍后再试"

    buckets = data.get("buckets", [])
    if not buckets:
        return "未找到额度信息"

    lines = ["大模型剩余额度："]
    for bucket in buckets:
        name = bucket["name"]
        current = bucket["current"]
        capacity = bucket["capacity"]
        remaining = capacity - current
        remaining_yuan = remaining / 1_000_000_000
        lines.append(f"  {name}: {remaining_yuan:.2f} 元")

    return "\n".join(lines)
