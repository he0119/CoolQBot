""" 复读排行榜
"""
import collections
from collections.abc import Sequence
from operator import itemgetter

from nonebot.adapters import Bot

from src.utils.annotated import GroupInfo
from src.utils.helpers import get_nickname

from ...models import Record
from ...recorder import Recorder


async def get_rank(
    bot: Bot,
    display_number: int,
    minimal_msg_number: int,
    display_total_number: bool,
    group_info: GroupInfo,
) -> str:
    """获取排行榜"""
    recorder = Recorder(group_info)

    if not await recorder.is_enabled():
        return "该群未开启复读功能，无法获取排行榜。"

    records = await recorder.get_records()

    ranking = Ranking(
        bot,
        records,
        display_number,
        minimal_msg_number,
        display_total_number,
        group_info,
    )
    str_data = await ranking.ranking()

    if not str_data:
        str_data = "暂时还没有满足条件的数据~>_<~"

    return str_data


class Ranking:
    """排行榜"""

    def __init__(
        self,
        bot: Bot,
        records: Sequence[Record],
        display_number: int,
        minimal_msg_number: int,
        display_total_number: bool,
        group_info: GroupInfo,
    ):
        self.bot = bot
        self.records = records
        self.display_number = display_number
        self.minimal_msg_number = minimal_msg_number
        self.display_total_number = display_total_number
        self.group_info = group_info
        self._nickname_cache = {}

    async def ranking(self):
        """合并两个排行榜"""
        self.repeat_list = {
            record.user_id: record.repeat_time for record in self.records
        }
        self.msg_number_list = {
            record.user_id: record.msg_number for record in self.records
        }

        repeat_rate_ranking = await self.repeat_rate_ranking()
        repeat_number_ranking = await self.repeat_number_ranking()

        if repeat_rate_ranking and repeat_number_ranking:
            return repeat_rate_ranking + "\n\n" + repeat_number_ranking

    async def repeat_number_ranking(self):
        """获取次数排行榜"""
        od = collections.OrderedDict(
            sorted(self.repeat_list.items(), key=itemgetter(1), reverse=True)
        )

        str_data = await self.ranking_str(od, "number")

        if str_data:
            return f"复读次数排行榜{str_data}"
        else:
            return None

    async def repeat_rate_ranking(self):
        """获取复读概率排行榜"""
        repeat_rate = self.get_repeat_rate(self.repeat_list, self.msg_number_list)
        od = collections.OrderedDict(
            sorted(repeat_rate.items(), key=itemgetter(1), reverse=True)
        )

        str_data = await self.ranking_str(od, "rate")

        if str_data:
            return f"Love Love Ranking{str_data}"
        else:
            return None

    async def ranking_str(self, sorted_list, list_type):
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
                    str_data += f"{v*100:.2f}%" if list_type == "rate" else f"{v}次"
                    i += 1
            else:
                return str_data
        return str_data

    @staticmethod
    def get_repeat_rate(repeat_list, msg_number_list):
        """获取复读概率表"""
        repeat_rate = {k: v / msg_number_list[k] for k, v in repeat_list.items()}
        return repeat_rate

    async def nikcname(self, user_id):
        """输入 QQ 号，返回群昵称，如果群昵称为空则返回 QQ 昵称"""
        if user_id in self._nickname_cache:
            return self._nickname_cache[user_id]
        else:
            name = await get_nickname(
                self.bot, user_id, **self.group_info.dict(exclude={"platform"})
            )
            self._nickname_cache[user_id] = name
            return name
