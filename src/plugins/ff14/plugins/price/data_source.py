""" 查询价格

https://universalis.app/docs/index.html?urls.primaryName=Universalis%20v2

https://github.com/thewakingsands/cafemaker/wiki
"""

from datetime import datetime
from typing import Optional

import httpx
from pydantic import BaseModel


class XIVAPIResultsItem(BaseModel):
    ID: int
    Icon: str
    Name: str
    Url: str
    UrlType: str
    _: str
    _Score: float


class XIVAPISearch(BaseModel):
    Results: list[XIVAPIResultsItem]


class UniversalisListingItem(BaseModel):
    lastReviewTime: datetime
    pricePerUnit: int
    quantity: int
    worldName: str | None
    """如果查询时提供的服务器名称而不是大区名称，这一项是空"""
    hq: bool


class UniversalisCurrentlyShown(BaseModel):
    itemID: int
    lastUploadTime: datetime
    listings: list[UniversalisListingItem]


async def search_item_id_by_name(name: str) -> int | None:
    """通过物品名称获取物品 ID"""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"https://cafemaker.wakingsands.com/search?string={name}")
        rjson = r.json()
        search = XIVAPISearch.parse_obj(rjson)
        for item in search.Results:
            if item.UrlType == "Item" and item.Name == name:
                return item.ID


async def get_item_price(name: str, world_or_dc: str) -> str:
    """通过物品 ID 获取物品价格"""
    item_id = await search_item_id_by_name(name)
    if not item_id:
        return f"抱歉，没有找到 {name}，请检查物品名称是否正确。"

    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://universalis.app/api/v2/{world_or_dc}/{item_id}?listings=6"
        )
        rjson = r.json()

        if "itemID" not in rjson:
            return f"抱歉，没有找到 {world_or_dc} 的数据，请检查大区或服务器名称是否正确。"

        data = UniversalisCurrentlyShown.parse_obj(rjson)

        items_info = []
        for item in data.listings:
            items_info.append(
                f"{item.pricePerUnit}*{item.quantity} {'HQ' if item.hq else ''} 服务器: {item.worldName if item.worldName is not None else world_or_dc}"
            )
        if items_info:
            items_info.insert(0, f"{name} 在市场的价格是:")
            # 使用本地时区
            items_info.append(
                f'数据更新时间: {data.lastUploadTime.astimezone().strftime("%Y年%m月%d日 %H时%M分")}'
            )
            return "\n".join(items_info)
        return f"抱歉，没有找到 {name} 的价格。"
