"""复读排行榜"""

import collections
from collections.abc import Sequence
from operator import itemgetter
from typing import Any

from nonebot_plugin_user import get_user_by_id

from src.plugins.repeat.models import MessageRecord
from src.plugins.repeat.recorder import get_recorder


async def get_rank(
    display_number: int,
    minimal_msg_number: int,
    display_total_number: bool,
    session_id: str,
) -> str:
    """获取排行榜"""
    recorder = get_recorder(session_id)

    if not await recorder.is_enabled():
        return "该群未开启复读功能，无法获取排行榜。"

    records = await recorder.get_records()

    ranking = Ranking(
        records,
        display_number,
        minimal_msg_number,
        display_total_number,
        session_id,
    )
    str_data = await ranking.ranking()

    if not str_data:
        str_data = "暂时还没有满足条件的数据~>_<~"

    return str_data


class Ranking:
    """排行榜"""

    def __init__(
        self,
        records: Sequence[MessageRecord],
        display_number: int,
        minimal_msg_number: int,
        display_total_number: bool,
        session_id: str,
    ):
        self.records = records
        self.display_number = display_number
        self.minimal_msg_number = minimal_msg_number
        self.display_total_number = display_total_number
        self.session_id = session_id
        self._nickname_cache = {}

    async def ranking(self) -> str | None:
        """合并两个排行榜"""
        self.repeat_list = {record.uid: record.repeat_time for record in self.records}
        self.msg_number_list = {record.uid: record.msg_number for record in self.records}

        repeat_rate_ranking = await self.repeat_rate_ranking()
        repeat_number_ranking = await self.repeat_number_ranking()

        if repeat_rate_ranking and repeat_number_ranking:
            return repeat_rate_ranking + "\n\n" + repeat_number_ranking

    async def repeat_number_ranking(self) -> str | None:
        """获取次数排行榜"""
        od = collections.OrderedDict(sorted(self.repeat_list.items(), key=itemgetter(1), reverse=True))

        str_data = await self.ranking_str(od, "number")

        if str_data:
            return f"复读次数排行榜{str_data}"
        else:
            return None

    async def repeat_rate_ranking(self) -> str | None:
        """获取复读概率排行榜"""
        repeat_rate = self.get_repeat_rate(self.repeat_list, self.msg_number_list)
        od = collections.OrderedDict(sorted(repeat_rate.items(), key=itemgetter(1), reverse=True))

        str_data = await self.ranking_str(od, "rate")

        if str_data:
            return f"Love Love Ranking{str_data}"
        else:
            return None

    async def ranking_str(self, sorted_list: collections.OrderedDict[int, Any], list_type: str) -> str:
        """获取排行榜文字"""
        i = 0
        str_data = ""
        for user_id, v in sorted_list.items():
            if i < self.display_number:
                if self.msg_number_list[user_id] >= self.minimal_msg_number:
                    name = await self.nikcname(user_id)
                    if self.display_total_number:
                        str_data += f"\n{name}({self.msg_number_list[user_id]})："
                    else:
                        str_data += f"\n{name}："
                    str_data += f"{v * 100:.2f}%" if list_type == "rate" else f"{v}次"
                    i += 1
            else:
                return str_data
        return str_data

    @staticmethod
    def get_repeat_rate(repeat_list: dict[int, int], msg_number_list: dict[int, int]) -> dict[int, float]:
        """获取复读概率表"""
        repeat_rate = {k: v / msg_number_list[k] for k, v in repeat_list.items()}
        return repeat_rate

    async def nikcname(self, user_id: int) -> str:
        """输入 QQ 号，返回用户昵称"""
        if user_id in self._nickname_cache:
            return self._nickname_cache[user_id]
        else:
            user = await get_user_by_id(user_id)
            self._nickname_cache[user_id] = user.name
            return user.name
