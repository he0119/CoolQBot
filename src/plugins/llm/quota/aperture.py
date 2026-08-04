"""Tailscale Aperture 额度查询 Provider。"""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from .base import BaseQuotaConfig, QuotaItem, QuotaProvider, QuotaResult


class ApertureQuotaConfig(BaseQuotaConfig):
    """Tailscale Aperture 额度接口配置。"""

    provider: Literal["aperture"]
    bucket: str = ""
    """仅显示指定额度桶；留空时显示接口返回的全部额度桶。"""


class ApertureBucket(BaseModel):
    """Aperture 额度桶响应中的必要字段。"""

    name: str
    current: Decimal


class ApertureResponse(BaseModel):
    """Aperture 额度响应。"""

    buckets: list[ApertureBucket]


class ApertureQuotaProvider(QuotaProvider):
    """Tailscale Aperture 额度查询。"""

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
