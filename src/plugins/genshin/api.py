""" 原神 API

参考 https://github.com/DGP-Studio/DGP.Genshin.MiHoYoAPI
"""
import hashlib
import json
import random
import time
from datetime import timedelta
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel
from pydantic.networks import AnyHttpUrl


class GameRole(BaseModel):
    """游戏角色信息"""

    game_biz: str
    region: str
    game_uid: int
    nickname: str
    level: int
    is_chosen: bool
    region_name: str
    is_official: bool


class Expedition(BaseModel):
    """派遣"""

    avatar_side_icon: AnyHttpUrl
    status: str
    remained_time: timedelta


class DailyNote(BaseModel):
    """实时便笺"""

    current_resin: int
    max_resin: int
    resin_recovery_time: timedelta
    finished_task_num: int
    total_task_num: int
    is_extra_task_reward_received: bool
    remain_resin_discount_num: int
    resin_discount_num_limit: int
    current_expedition_num: int
    max_expedition_num: int
    expeditions: list[Expedition]
    current_home_coin: int
    max_home_coin: int
    home_coin_recovery_time: timedelta


class Genshin:
    def __init__(self, cookie):
        self.cookie = cookie

    @staticmethod
    def md5(text: str) -> str:
        md5 = hashlib.md5()
        md5.update(text.encode())
        return md5.hexdigest()

    def get_ds(self, data: Optional[Any] = None, params: Optional[dict] = None) -> str:
        """生成 ds"""
        salt = "xV8v4Qu54lUKrEYFZkJhB8cuOh9Asafs"
        t = str(int(time.time()))
        r = str(random.randint(100000, 200000))
        b = json.dumps(data) if data else ""
        q = urlencode(params) if params else ""
        c = self.md5(f"salt={salt}&t={t}&r={r}&b={b}&q={q}")
        return f"{t},{r},{c}"

    def get_ua(
        self,
        referer: Optional[str] = None,
        with_ds: bool = False,
        data: Optional[Any] = None,
        params: Optional[dict] = None,
    ):
        """获取 UA"""
        ua = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) miHoYoBBS/2.16.1",
            "Referer": referer if referer else "https://webstatic.mihoyo.com/",
            "Cookie": self.cookie,
            "X-Requested-With": "com.mihoyo.hyperion",
        }
        if with_ds:
            ua.update(
                {
                    "x-rpc-client_type": "5",
                    "x-rpc-app_version": "2.16.1",
                    "x-rpc-device_id": "5d8b09e710294d7aa0e7f46d4738fefc",
                    "ds": self.get_ds(data=data, params=params),
                }
            )
        return ua

    async def get_game_role(self) -> Optional[GameRole]:
        """获取角色信息"""
        url = "https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie?game_biz=hk4e_cn"

        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=self.get_ua())
            rjson = r.json()
            for role in rjson["data"]["list"]:
                role = GameRole.parse_obj(role)
                if role.region == "cn_gf01":
                    return role

    async def daily_note(self) -> str:
        """实时便笺信息"""
        url = (
            "https://api-takumi-record.mihoyo.com/game_record/app/genshin/api/dailyNote"
        )
        referer = (
            "https://webstatic.mihoyo.com/app/community-game-records/index.html?v=6"
        )
        role = await self.get_game_role()
        if not role:
            return "没有找到角色信息"

        params = {"role_id": role.game_uid, "server": role.region}
        async with httpx.AsyncClient() as client:
            r = await client.get(
                url,
                headers=self.get_ua(referer=referer, with_ds=True, params=params),
                params=params,
            )
            rjson = r.json()
            if rjson["retcode"] == 0:
                note = DailyNote.parse_obj(rjson["data"])

        return "失败"
