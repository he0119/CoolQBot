"""带本地缓存的远程 JSON 数据。"""

import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
from nonebot.log import logger

from src.utils.files import write_bytes_atomic

DEFAULT_MAX_BYTES = 1024 * 1024
DEFAULT_USER_AGENT = "CoolQBot (+https://github.com/he0119/CoolQBot)"
_UNSET = object()


class RemoteDataError(RuntimeError):
    """远程数据读取或校验失败。"""


class RemoteDataTooLargeError(RemoteDataError):
    """远程数据超过大小限制。"""


class RemoteJsonData[T]:
    """下载、校验并原子缓存远程 JSON 数据。

    首次读取优先使用本地缓存；缓存不存在或损坏时才访问网络。显式调用
    :meth:`update` 会强制下载，但只有在 HTTP、JSON 解析和业务校验全部成功后
    才替换内存及磁盘缓存。
    """

    def __init__(
        self,
        url: str,
        cache_file: Callable[[], Path],
        process_data: Callable[[Any], T],
        *,
        max_bytes: int = DEFAULT_MAX_BYTES,
        timeout: float = 10.0,
    ) -> None:
        if max_bytes <= 0:
            raise ValueError("max_bytes 必须大于 0")

        self.url = url
        self._cache_file = cache_file
        self._process_data = process_data
        self._max_bytes = max_bytes
        self._timeout = timeout
        self._data: T | object = _UNSET
        self._lock = asyncio.Lock()

    @property
    def cache_file(self) -> Path:
        """当前配置对应的缓存文件路径。"""
        return self._cache_file()

    @property
    async def data(self) -> T:
        """读取内存或磁盘缓存，必要时从网络初始化。"""
        if self._data is not _UNSET:
            return self._data  # type: ignore[return-value]

        async with self._lock:
            if self._data is not _UNSET:
                return self._data  # type: ignore[return-value]

            cache_file = self.cache_file
            if cache_file.is_file():
                try:
                    data = self._load_local(cache_file)
                except Exception as e:
                    logger.warning("本地远程数据缓存损坏，将重新下载 {}: {}", cache_file, e)
                else:
                    self._data = data
                    return data

            return await self._update_locked()

    async def update(self) -> T:
        """强制刷新数据；失败时保留原内存和磁盘缓存。"""
        async with self._lock:
            return await self._update_locked()

    def clear_memory_cache(self) -> None:
        """清除内存缓存，使下次读取重新检查磁盘。"""
        self._data = _UNSET

    def _load_local(self, cache_file: Path) -> T:
        content = cache_file.read_bytes()
        self._check_size(len(content))
        return self._process_data(json.loads(content))

    async def _update_locked(self) -> T:
        cache_file = self.cache_file
        try:
            content = await self._download()
            data = self._process_data(json.loads(content))
            write_bytes_atomic(cache_file, content)
        except RemoteDataError:
            raise
        except Exception as e:
            raise RemoteDataError(f"更新远程数据失败：{e}") from e

        self._data = data
        logger.info("已更新远程数据缓存 {} -> {}", self.url, cache_file)
        return data

    async def _download(self) -> bytes:
        headers = {"User-Agent": DEFAULT_USER_AGENT}
        async with (
            httpx.AsyncClient(timeout=self._timeout, follow_redirects=True, headers=headers) as client,
            client.stream("GET", self.url) as response,
        ):
            response.raise_for_status()
            if content_length := response.headers.get("Content-Length"):
                try:
                    self._check_size(int(content_length))
                except ValueError as e:
                    raise RemoteDataError("远程数据的 Content-Length 无效") from e

            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                self._check_size(len(content))
            return bytes(content)

    def _check_size(self, size: int) -> None:
        if size > self._max_bytes:
            raise RemoteDataTooLargeError(f"远程数据超过 {self._max_bytes} 字节限制")
