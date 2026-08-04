"""按模型配置查询大模型剩余额度。"""

from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING, Annotated

from nonebot.log import logger
from pydantic import Field

from .aperture import ApertureQuotaConfig, ApertureQuotaProvider
from .base import BaseQuotaConfig, QuotaError, QuotaItem, QuotaProvider, QuotaResult
from .deepseek import DeepSeekQuotaConfig, DeepSeekQuotaProvider

if TYPE_CHECKING:
    from decimal import Decimal

    from ..config import ModelConfig


QuotaConfig = Annotated[ApertureQuotaConfig | DeepSeekQuotaConfig, Field(discriminator="provider")]
"""单个模型的额度查询配置。"""


QUOTA_PROVIDERS: dict[str, type[QuotaProvider]] = {
    "aperture": ApertureQuotaProvider,
    "deepseek": DeepSeekQuotaProvider,
}
"""额度 Provider 注册表。"""


def _format_amount(amount: Decimal, currency: str) -> str:
    if currency == "CNY":
        return f"{amount:.2f} 元"
    if currency == "USD":
        return f"${amount:.2f}"
    return f"{amount:.2f} {currency}"


def format_quota(model_name: str, result: QuotaResult) -> str:
    """把统一额度结果格式化为聊天消息。"""
    if not result.items:
        return f"未找到 {model_name} 的额度信息"

    lines = [f"{model_name} 剩余额度："]
    if result.available is False:
        lines.append("  当前账户无可用余额")
    for item in result.items:
        line = f"  {item.name}: {_format_amount(item.amount, item.currency)}"
        if item.details:
            details = "，".join(f"{name} {_format_amount(amount, item.currency)}" for name, amount in item.details)
            line += f"（{details}）"
        lines.append(line)
    return "\n".join(lines)


async def get_quota(model: ModelConfig) -> str:
    """根据模型配置选择 Provider 并查询额度。"""
    if model.quota is None:
        raise QuotaError(f"模型 {model.name} 未配置额度查询")
    provider = QUOTA_PROVIDERS[model.quota.provider](model.quota, model)
    started_at = perf_counter()
    logger.info("LLM 额度查询开始（模型={}，provider={}）", model.name, model.quota.provider)
    try:
        result = await provider.query()
    except QuotaError:
        logger.warning(
            "LLM 额度查询失败（模型={}，provider={}，耗时={:.3f}s）",
            model.name,
            model.quota.provider,
            perf_counter() - started_at,
        )
        raise
    logger.info(
        "LLM 额度查询完成（模型={}，provider={}，项目={}，可用={}，耗时={:.3f}s）",
        model.name,
        model.quota.provider,
        len(result.items),
        result.available,
        perf_counter() - started_at,
    )
    return format_quota(model.name, result)


__all__ = [
    "QUOTA_PROVIDERS",
    "ApertureQuotaConfig",
    "ApertureQuotaProvider",
    "BaseQuotaConfig",
    "DeepSeekQuotaConfig",
    "DeepSeekQuotaProvider",
    "QuotaConfig",
    "QuotaError",
    "QuotaItem",
    "QuotaProvider",
    "QuotaResult",
    "format_quota",
    "get_quota",
]
