""" 原神 API

参考 https://github.com/DGP-Studio/DGP.Genshin.MiHoYoAPI
"""
import hashlib
import json
import random
import time
from datetime import timedelta
from inspect import cleandoc
from typing import Any
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel
from pydantic.networks import AnyHttpUrl

from src.utils.helpers import timedelta_to_chinese


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

    def get_ds(self, data: Any | None = None, params: dict | None = None) -> str:
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
        referer: str | None = None,
        with_ds: bool = False,
        data: Any | None = None,
        params: dict | None = None,
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

    async def get_game_role(self) -> GameRole | None:
        """获取角色信息"""
        url = "https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie?game_biz=hk4e_cn"

        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=self.get_ua())
            rjson = r.json()
            for role in rjson["data"]["list"]:
                role = GameRole.parse_obj(role)
                if role.region == "cn_gf01":
                    return role

    async def get_daily_note(self, role: GameRole) -> DailyNote | None:
        """获取实时便笺信息"""
        url = (
            "https://api-takumi-record.mihoyo.com/game_record/app/genshin/api/dailyNote"
        )
        referer = (
            "https://webstatic.mihoyo.com/app/community-game-records/index.html?v=6"
        )

        params = {"role_id": role.game_uid, "server": role.region}
        async with httpx.AsyncClient() as client:
            r = await client.get(
                url,
                headers=self.get_ua(referer=referer, with_ds=True, params=params),
                params=params,
            )
            rjson = r.json()
            if rjson["retcode"] == 0:
                return DailyNote.parse_obj(rjson["data"])

    async def daily_note(self) -> str:
        """实时便笺信息"""
        role = await self.get_game_role()
        if not role:
            return "没有找到角色信息，请检查账号是否正确"

        note = await self.get_daily_note(role)
        if not note:
            return "获取实时便笺失败，请稍后再试"

        expeditions = ""
        for i, expedition in enumerate(note.expeditions, 1):
            if expedition.status == "Ongoing":
                expeditions += (
                    f"\n角色{i}: {timedelta_to_chinese(expedition.remained_time)}后完成派遣"
                )
            elif expedition.status == "Finished":
                expeditions += f"\n角色{i}: 已完成派遣"

        # 每日委托奖励的说明
        if note.is_extra_task_reward_received == True:
            extra_task_reward_description = "已领取「每日委托」奖励"
        elif note.finished_task_num != note.total_task_num:
            extra_task_reward_description = "今日完成委托次数不足"
        else:
            extra_task_reward_description = "「每日委托」奖励待领取"

        # 原粹树脂的说明
        if note.resin_recovery_time:
            resin_description = f"{timedelta_to_chinese(note.resin_recovery_time)}后全部恢复"
        else:
            resin_description = "已完全恢复"

        # 洞天宝钱的说明
        if note.home_coin_recovery_time:
            home_coin_description = (
                f"{timedelta_to_chinese(note.home_coin_recovery_time)}后达到存储上限"
            )
        else:
            home_coin_description = "已满"

        reply = cleandoc(
            f"""
            原粹树脂: {note.current_resin}/{note.max_resin} ({resin_description})
            洞天宝钱: {note.current_home_coin}/{note.max_home_coin} ({home_coin_description})
            每日委托任务: {note.finished_task_num}/{note.total_task_num} ({extra_task_reward_description})
            值得铭记的强敌: {note.remain_resin_discount_num}/{note.resin_discount_num_limit} (本周剩余消耗减半次数)
            探索派遣: {note.current_expedition_num}/{note.max_expedition_num}
            """
        )

        return reply + expeditions
