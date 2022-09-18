""" 时尚品鉴 """
import re
from typing import Optional

import httpx


async def get_all_post():
    """获取最近发布的视频"""
    async with httpx.AsyncClient() as client:
        # https://space.bilibili.com/15503317/video
        # 这位 UP 主一直在发时尚品鉴的攻略视频
        # https://api.bilibili.com/x/space/arc/search?mid=15503317&ps=30&tid=0&pn=1&keyword=&order=pubdate&jsonp=jsonp
        params = {
            "mid": 15503317,
            "ps": 30,
            "tid": 0,
            "pn": 1,
            "keyword": "",
            "order": "pubdate",
            "jsonp": "jsonp",
        }
        r = await client.get(
            "https://api.bilibili.com/x/space/arc/search",
            params=params,
            timeout=4.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1343.42"
            },
        )
        rjson = r.json()
        if rjson["code"] == 0:
            return rjson["data"]["list"]["vlist"]
        else:
            return []


async def get_latest_nuannuan() -> Optional[str]:
    """获取最新时尚品鉴"""
    cards = await get_all_post()
    if not cards:
        return
    for card in cards:
        match = re.match(r"【FF14\/时尚品鉴】第\d+期 满分攻略", card["title"])
        if match:
            title = card["title"]
            description = card["description"].replace("个人攻略网站", "游玩C哩酱攻略站")
            url = f"https://www.bilibili.com/video/{card['bvid']}"
            return "\n".join([title, description, url])
