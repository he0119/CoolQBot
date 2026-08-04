"""额度查询 Provider 抽象与共用数据结构。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, ValidationError

from ..providers.base import USER_AGENT

if TYPE_CHECKING:
    from collections.abc import Hashable
    from decimal import Decimal

    from ..config import ModelConfig


class BaseQuotaConfig(BaseModel):
    """额度查询的共用配置。"""

    api_url: str = ""
    """完整的额度接口地址；留空时回退到全局 LLM 服务地址。"""
    api_key: str = ""
    """额度接口密钥；留空时由具体 Provider 决定是否复用模型密钥。"""
    proxy: str | None = None
    """额度查询代理地址；留空时复用模型代理。"""
    timeout: int = 10
    """额度查询超时时间（秒）。"""


class QuotaError(Exception):
    """额度查询失败。"""


@dataclass
class QuotaItem:
    """统一后的单项额度信息。"""

    name: str
    amount: Decimal
    currency: str
    details: list[tuple[str, Decimal]] = field(default_factory=list)


@dataclass
class QuotaResult:
    """统一后的额度查询结果。"""

    items: list[QuotaItem]
    available: bool | None = None


class QuotaProvider(ABC):
    """额度查询 Provider 基类。"""

    endpoint_path: str
    """未显式配置 API 地址时，相对于服务域名根目录的接口路径。"""

    def __init__(self, config: BaseQuotaConfig, model: ModelConfig) -> None:
        self.config = config
        self.model = model

    @property
    def api_url(self) -> str:
        """解析完整的额度查询地址。"""
        if self.config.api_url:
            return self.config.api_url

        # 延迟导入，避免配置模型引用额度配置时产生循环依赖。
        from ..config import plugin_config

        base_url = plugin_config.base_url or self.model.base_url
        if base_url:
            return urljoin(base_url, self.endpoint_path)
        raise QuotaError("额度查询未配置 API 地址或 LLM__BASE_URL")

    def build_headers(self) -> dict[str, str]:
        """构造请求头。"""
        return {"User-Agent": USER_AGENT}

    @property
    def request_key(self) -> tuple[object, ...]:
        """标识可合并为同一次 HTTP 请求的配置。"""
        proxy = self.config.proxy if self.config.proxy is not None else self.model.proxy
        return (
            type(self),
            self.api_url,
            tuple(sorted(self.build_headers().items())),
            proxy,
            self.config.timeout,
        )

    @property
    def result_selector(self) -> Hashable:
        """标识同一请求结果中的模型视图；子类可按桶等筛选项覆盖。"""
        return None

    @abstractmethod
    def parse_response(self, data: object) -> QuotaResult:
        """解析服务商响应。"""

    def select_result(self, result: QuotaResult) -> QuotaResult:
        """从共享查询结果中选出当前模型需要的部分。"""
        return result

    async def query_shared(self) -> QuotaResult:
        """请求并解析可供同组模型共享的完整额度信息。"""
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

    async def query(self) -> QuotaResult:
        """查询并筛选当前模型的额度信息。"""
        return self.select_result(await self.query_shared())
