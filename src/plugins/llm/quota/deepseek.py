"""DeepSeek 官方余额查询 Provider。"""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from .base import BaseQuotaConfig, QuotaError, QuotaItem, QuotaProvider, QuotaResult


class DeepSeekQuotaConfig(BaseQuotaConfig):
    """DeepSeek 官方余额接口配置。"""

    provider: Literal["deepseek"]


class DeepSeekBalance(BaseModel):
    """DeepSeek 单币种余额。"""

    currency: Literal["CNY", "USD"]
    total_balance: Decimal
    granted_balance: Decimal
    topped_up_balance: Decimal


class DeepSeekResponse(BaseModel):
    """DeepSeek 余额响应。"""

    is_available: bool
    balance_infos: list[DeepSeekBalance]


class DeepSeekQuotaProvider(QuotaProvider):
    """DeepSeek 官方余额查询。"""

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
