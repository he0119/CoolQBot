"""查询价格

https://universalis.app/docs/index.html?urls.primaryName=Universalis%20v2

https://api.ffxivteamcraft.com/search
"""

from datetime import datetime

import httpx
from pydantic import BaseModel, Field

from src.plugins.llm.tools import registry


class TeamcraftSearchItem(BaseModel):
    item_id: int = Field(alias="itemId")
    name: str = Field(alias="zh")


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


async def search_item_id_by_name(name: str) -> TeamcraftSearchItem | None:
    """通过物品名称获取物品 ID"""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://api.ffxivteamcraft.com/search",
            params={"query": name, "type": "Item", "sort": "desc", "lang": "zh"},
        )
        r.raise_for_status()
        search = [TeamcraftSearchItem.model_validate(item) for item in r.json()]

        for item in search:
            if item.name == name:
                return item
        return search[0] if search else None


async def get_item_price(name: str, world_or_dc: str) -> str:
    """通过物品名称获取物品价格"""
    try:
        item = await search_item_id_by_name(name)
    except httpx.HTTPError:
        return "抱歉，网络出错，无法获取物品 ID，请稍后再试。"

    if not item:
        return f"抱歉，没有找到 {name}，请检查物品名称是否正确。"

    async with httpx.AsyncClient() as client:
        r = await client.get(f"https://universalis.app/api/v2/{world_or_dc}/{item.item_id}?listings=6")
        rjson = r.json()

        if "itemID" not in rjson:
            return f"抱歉，没有找到 {world_or_dc} 的数据，请检查大区或服务器名称是否正确。"

        data = UniversalisCurrentlyShown.model_validate(rjson)

        items_info = []
        for listitem in data.listings:
            items_info.append(
                f"{listitem.pricePerUnit}*{listitem.quantity} {'HQ' if listitem.hq else ''} 服务器: {listitem.worldName if listitem.worldName is not None else world_or_dc}"
            )
        if items_info:
            items_info.insert(0, f"{item.name} 在市场的价格是:")
            # 使用本地时区
            items_info.append(f"数据更新时间: {data.lastUploadTime.astimezone().strftime('%Y年%m月%d日 %H时%M分')}")
            return "\n".join(items_info)
        return f"抱歉，没有找到 {item.name} 的价格。"


@registry.register(
    "query_ff14_item_price",
    "查询最终幻想 XIV 国服指定物品在服务器或大区中的当前市场最低价",
)
async def query_ff14_item_price(item_name: str, world_or_dc: str = "猫小胖") -> str:
    """查询最终幻想 XIV 国服市场价格

    Args:
        item_name: 物品中文名称
        world_or_dc: 国服服务器或大区名称，省略时查询猫小胖大区
    """
    try:
        return await get_item_price(item_name, world_or_dc)
    except httpx.HTTPError:
        return "抱歉，网络出错，无法获取物品价格，请稍后再试。"
