"""Provider 抽象与共用工具"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from ..config import ModelConfig
    from ..schemas import Completion, Message, ToolParam


class ProviderError(Exception):
    """调用大模型失败"""


async def iter_sse(response: httpx.Response) -> AsyncIterator[tuple[str, Any]]:
    """解析 SSE 流，产出 (事件名, 已解析的 JSON 数据)

    三种格式的 SSE 都遵循同一套行协议，差别只在事件名与数据结构：

    - Chat Completions 不发送 `event:` 行，以 `data: [DONE]` 结束
    - Responses 与 Anthropic 都发送 `event:` 行，事件名决定数据含义

    因此这里统一按行解析，事件名缺失时以空字符串表示。
    """
    event = ""
    async for line in response.aiter_lines():
        line = line.rstrip("\r")
        # 空行代表一个事件结束，重置事件名
        if not line:
            event = ""
            continue
        # 以冒号开头的是注释（心跳），直接忽略
        if line.startswith(":"):
            continue
        if ":" not in line:
            continue

        field, _, value = line.partition(":")
        value = value.lstrip()
        if field == "event":
            event = value
        elif field == "data":
            if value == "[DONE]":
                return
            try:
                yield event, json.loads(value)
            except json.JSONDecodeError:
                # 单个数据块解析失败不应中断整个流
                continue


class Provider(ABC):
    """大模型 API 客户端基类

    子类只需实现请求体构造与响应解析，HTTP 交互由基类统一处理。
    """

    def __init__(self, config: ModelConfig) -> None:
        self.config = config

    @property
    @abstractmethod
    def endpoint(self) -> str:
        """请求地址"""

    @abstractmethod
    def build_headers(self) -> dict[str, str]:
        """构造请求头"""

    @abstractmethod
    def build_payload(
        self,
        messages: list[Message],
        tools: list[ToolParam] | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """构造请求体"""

    @abstractmethod
    def parse_response(self, data: dict[str, Any]) -> Completion:
        """解析非流式响应"""

    @abstractmethod
    async def parse_stream(self, response: httpx.Response) -> Completion:
        """解析流式响应"""

    async def chat(self, messages: list[Message], tools: list[ToolParam] | None = None) -> Completion:
        """发起一次对话请求"""
        stream = bool(self.config.stream)
        payload = self.build_payload(messages, tools, stream=stream)
        headers = self.build_headers()

        try:
            if stream:
                return await self._request_stream(payload, headers)
            return await self._request(payload, headers)
        except httpx.TimeoutException as e:
            raise ProviderError("请求超时，请稍后重试") from e
        except httpx.HTTPError as e:
            raise ProviderError(f"网络请求失败：{e}") from e

    async def _request(self, payload: dict[str, Any], headers: dict[str, str]) -> Completion:
        async with httpx.AsyncClient(proxy=self.config.proxy) as client:
            response = await client.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=self.config.timeout,
            )
        data = response.json()
        self.raise_for_error(data, response.status_code)
        return self.parse_response(data)

    async def _request_stream(self, payload: dict[str, Any], headers: dict[str, str]) -> Completion:
        # 流式请求不设总超时，避免长回复被中途掐断
        async with httpx.AsyncClient(proxy=self.config.proxy, timeout=None) as client:
            async with client.stream("POST", self.endpoint, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    await response.aread()
                    self.raise_for_error(response.json(), response.status_code)
                return await self.parse_stream(response)

    def raise_for_error(self, data: dict[str, Any], status_code: int = 200) -> None:
        """检查响应中的错误信息

        三种格式的错误体都是 `{"error": {"message": ...}}`，
        少数服务商会直接返回 `{"message": ...}`。
        """
        error = data.get("error")
        if isinstance(error, dict):
            raise ProviderError(str(error.get("message") or error))
        if isinstance(error, str):
            raise ProviderError(error)
        if status_code != 200:
            message = data.get("message") or f"HTTP {status_code}"
            raise ProviderError(str(message))
