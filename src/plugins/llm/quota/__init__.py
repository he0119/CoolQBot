"""按模型配置查询大模型剩余额度。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING, Annotated

from nonebot.log import logger
from pydantic import Field

from .aperture import ApertureQuotaConfig, ApertureQuotaProvider
from .base import BaseQuotaConfig, QuotaError, QuotaItem, QuotaProvider, QuotaResult
from .deepseek import DeepSeekQuotaConfig, DeepSeekQuotaProvider

if TYPE_CHECKING:
    from collections.abc import Hashable
    from decimal import Decimal

    from ..config import ModelConfig


QuotaConfig = Annotated[ApertureQuotaConfig | DeepSeekQuotaConfig, Field(discriminator="provider")]
"""单个模型的额度查询配置。"""


QUOTA_PROVIDERS: dict[str, type[QuotaProvider]] = {
    "aperture": ApertureQuotaProvider,
    "deepseek": DeepSeekQuotaProvider,
}
"""额度 Provider 注册表。"""


@dataclass
class _BatchQuotaResult:
    """单个模型的批量查询结果及其可合并展示键。"""

    model_name: str
    display_key: Hashable
    result: QuotaResult | None = None
    error: str = ""


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


async def _query_provider_group(
    request_key: Hashable,
    items: list[tuple[ModelConfig, QuotaProvider]],
) -> list[_BatchQuotaResult]:
    """发起一次共享请求，并为组内模型分别筛选结果。"""
    provider = items[0][1]
    started_at = perf_counter()
    try:
        shared_result = await provider.query_shared()
    except QuotaError as e:
        logger.warning(
            "LLM 批量额度请求失败（provider={}，模型={}，耗时={:.3f}s）",
            items[0][0].quota.provider if items[0][0].quota else "unknown",
            len(items),
            perf_counter() - started_at,
        )
        return [
            _BatchQuotaResult(
                model_name=model.name,
                display_key=("request-error", request_key, str(e)),
                error=str(e),
            )
            for model, _ in items
        ]

    logger.info(
        "LLM 批量额度请求完成（provider={}，模型={}，项目={}，耗时={:.3f}s）",
        items[0][0].quota.provider if items[0][0].quota else "unknown",
        len(items),
        len(shared_result.items),
        perf_counter() - started_at,
    )
    return [
        _BatchQuotaResult(
            model_name=model.name,
            display_key=("result", request_key, item_provider.result_selector),
            result=item_provider.select_result(shared_result),
        )
        for model, item_provider in items
    ]


def _format_batch_results(results: list[_BatchQuotaResult]) -> str:
    """按首次出现顺序合并相同额度视图并格式化。"""
    grouped: dict[Hashable, list[_BatchQuotaResult]] = {}
    for result in results:
        grouped.setdefault(result.display_key, []).append(result)

    sections: list[str] = []
    for items in grouped.values():
        names = "、".join(item.model_name for item in items)
        first = items[0]
        if first.result is not None:
            sections.append(format_quota(names, first.result))
        else:
            sections.append(f"{names}：{first.error}")
    return "\n\n".join(sections)


async def get_quotas(models: list[ModelConfig]) -> str:
    """批量查询模型额度，合并相同请求并并发执行不同请求。"""
    if not models:
        raise QuotaError("没有可查询额度的模型")

    started_at = perf_counter()
    request_groups: dict[Hashable, list[tuple[ModelConfig, QuotaProvider]]] = {}
    results: list[_BatchQuotaResult] = []
    for index, model in enumerate(models):
        if model.quota is None:
            results.append(
                _BatchQuotaResult(
                    model_name=model.name,
                    display_key=("not-configured",),
                    error="未配置额度查询",
                )
            )
            continue

        provider = QUOTA_PROVIDERS[model.quota.provider](model.quota, model)
        try:
            request_key = provider.request_key
        except QuotaError as e:
            results.append(
                _BatchQuotaResult(
                    model_name=model.name,
                    display_key=("setup-error", index),
                    error=str(e),
                )
            )
            continue
        request_groups.setdefault(request_key, []).append((model, provider))

    logger.info("LLM 批量额度查询开始（模型={}，请求={}）", len(models), len(request_groups))
    queried = await asyncio.gather(
        *(_query_provider_group(request_key, items) for request_key, items in request_groups.items())
    )
    results.extend(item for group in queried for item in group)

    order = {model.name: index for index, model in enumerate(models)}
    results.sort(key=lambda item: order[item.model_name])
    logger.info(
        "LLM 批量额度查询完成（模型={}，请求={}，失败={}，耗时={:.3f}s）",
        len(models),
        len(request_groups),
        sum(bool(item.error) for item in results),
        perf_counter() - started_at,
    )
    return _format_batch_results(results)


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
    "get_quotas",
]
