"""按模型配置查询大模型剩余额度"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from time import perf_counter
from typing import TYPE_CHECKING, Literal

import httpx
from nonebot.log import logger
from pydantic import BaseModel, ValidationError

from .config import plugin_config
from .providers.base import USER_AGENT

if TYPE_CHECKING:
    from .config import ApertureQuotaConfig, BaseQuotaConfig, DeepSeekQuotaConfig, ModelConfig


class QuotaError(Exception):
    """额度查询失败"""


@dataclass
class QuotaItem:
    """统一后的单项额度信息"""

    name: str
    amount: Decimal
    currency: str
    details: list[tuple[str, Decimal]] = field(default_factory=list)


@dataclass
class QuotaResult:
    """统一后的额度查询结果"""

    items: list[QuotaItem]
    available: bool | None = None


class ApertureBucket(BaseModel):
    """Aperture 额度桶响应中的必要字段"""

    name: str
    current: Decimal


class ApertureResponse(BaseModel):
    """Aperture 额度响应"""

    buckets: list[ApertureBucket]


class DeepSeekBalance(BaseModel):
    """DeepSeek 单币种余额"""

    currency: Literal["CNY", "USD"]
    total_balance: Decimal
    granted_balance: Decimal
    topped_up_balance: Decimal


class DeepSeekResponse(BaseModel):
    """DeepSeek 余额响应"""

    is_available: bool
    balance_infos: list[DeepSeekBalance]


class QuotaProvider(ABC):
    """额度查询 provider 基类"""

    endpoint_path: str
    """未显式配置 API 地址时追加到服务地址的路径"""

    def __init__(self, config: BaseQuotaConfig, model: ModelConfig) -> None:
        self.config = config
        self.model = model

    @property
    def api_url(self) -> str:
        """完整的额度查询地址"""
        if self.config.api_url:
            return self.config.api_url
        base_url = plugin_config.base_url or self.model.base_url
        if base_url:
            return f"{base_url.rstrip('/')}{self.endpoint_path}"
        raise QuotaError("额度查询未配置 API 地址或 LLM__BASE_URL")

    def build_headers(self) -> dict[str, str]:
        """构造请求头"""
        return {"User-Agent": USER_AGENT}

    @abstractmethod
    def parse_response(self, data: object) -> QuotaResult:
        """解析服务商响应"""

    async def query(self) -> QuotaResult:
        """请求并解析额度信息"""
        proxy = self.config.proxy if self.config.proxy is not None else self.model.proxy
        try:
            async with httpx.AsyncClient(proxy=proxy) as client:
                response = await client.get(
                    self.api_url,
                    headers=self.build_headers(),
                    timeout=self.config.timeout,
                )
                response.raise_for_status()
                return self.parse_response(response.json())
        except httpx.TimeoutException as e:
            raise QuotaError("额度查询超时，请稍后再试") from e
        except (httpx.HTTPError, ValidationError, ValueError) as e:
            raise QuotaError("获取额度信息失败，请稍后再试") from e


class ApertureQuotaProvider(QuotaProvider):
    """Tailscale Aperture 额度查询"""

    config: ApertureQuotaConfig
    endpoint_path = "/api/quotas"

    def build_headers(self) -> dict[str, str]:
        headers = super().build_headers()
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def parse_response(self, data: object) -> QuotaResult:
        response = ApertureResponse.model_validate(data)
        buckets = response.buckets
        if self.config.bucket:
            buckets = [bucket for bucket in buckets if bucket.name == self.config.bucket]
        return QuotaResult(
            items=[
                QuotaItem(
                    name=bucket.name,
                    amount=bucket.current / Decimal("1000000000"),
                    currency="CNY",
                )
                for bucket in buckets
            ]
        )


class DeepSeekQuotaProvider(QuotaProvider):
    """DeepSeek 官方余额查询"""

    config: DeepSeekQuotaConfig
    endpoint_path = "/user/balance"

    def build_headers(self) -> dict[str, str]:
        api_key = self.config.api_key or self.model.api_key
        if not api_key:
            raise QuotaError("DeepSeek 额度查询未配置 API 密钥")
        return {
            **super().build_headers(),
            "Authorization": f"Bearer {api_key}",
        }

    def parse_response(self, data: object) -> QuotaResult:
        response = DeepSeekResponse.model_validate(data)
        return QuotaResult(
            available=response.is_available,
            items=[
                QuotaItem(
                    name=balance.currency,
                    amount=balance.total_balance,
                    currency=balance.currency,
                    details=[
                        ("赠金", balance.granted_balance),
                        ("充值", balance.topped_up_balance),
                    ],
                )
                for balance in response.balance_infos
            ],
        )


QUOTA_PROVIDERS: dict[str, type[QuotaProvider]] = {
    "aperture": ApertureQuotaProvider,
    "deepseek": DeepSeekQuotaProvider,
}
"""额度 provider 注册表"""


def _format_amount(amount: Decimal, currency: str) -> str:
    if currency == "CNY":
        return f"{amount:.2f} 元"
    if currency == "USD":
        return f"${amount:.2f}"
    return f"{amount:.2f} {currency}"


def format_quota(model_name: str, result: QuotaResult) -> str:
    """把统一额度结果格式化为聊天消息"""
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
    """根据模型配置选择 provider 并查询额度"""
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
