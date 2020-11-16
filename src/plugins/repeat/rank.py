""" 复读排行榜
"""
import collections
from operator import itemgetter

from src.utils.helpers import get_first_bot

from .recorder import recorder


async def get_rank(
    display_number: int, minimal_msg_number: int, display_total_number: int,
    group_id: int
) -> str:
    """ 获取排行榜 """
    repeat_list = recorder.repeat_list(group_id)
    msg_number_list = recorder.msg_number_list(group_id)

    ranking = Ranking(
        group_id, display_number, minimal_msg_number, display_total_number,
        repeat_list, msg_number_list
    )
    str_data = await ranking.ranking()

    if not str_data:
        str_data = '暂时还没有满足条件的数据~>_<~'

    return str_data


class Ranking:
    """ 排行榜
    """
    def __init__(
        self, group_id, display_number, minimal_msg_number,
        display_total_number, repeat_list, msg_number_list
    ):
        self.group_id = group_id
        self.display_number = display_number
        self.minimal_msg_number = minimal_msg_number
        self.display_total_number = display_total_number
        self.repeat_list = repeat_list
        self.msg_number_list = msg_number_list

    async def ranking(self):
        """ 合并两个排行榜
        """
        repeat_rate_ranking = await self.repeat_rate_ranking()
        repeat_number_ranking = await self.repeat_number_ranking()

        if repeat_rate_ranking and repeat_number_ranking:
            return repeat_rate_ranking + '\n\n' + repeat_number_ranking

    async def repeat_number_ranking(self):
        """ 获取次数排行榜
        """
        od = collections.OrderedDict(
            sorted(self.repeat_list.items(), key=itemgetter(1), reverse=True)
        )

        str_data = await self.ranking_str(od, 'number')

        if str_data:
            return f'复读次数排行榜{str_data}'
        else:
            return None

    async def repeat_rate_ranking(self):
        """ 获取复读概率排行榜
        """
        repeat_rate = self.get_repeat_rate(
            self.repeat_list, self.msg_number_list
        )
        od = collections.OrderedDict(
            sorted(repeat_rate.items(), key=itemgetter(1), reverse=True)
        )

        str_data = await self.ranking_str(od, 'rate')

        if str_data:
            return f'Love Love Ranking{str_data}'
        else:
            return None

    async def ranking_str(self, sorted_list, list_type):
        """ 获取排行榜文字
        """
        i = 0
        str_data = ''
        for user_id, v in sorted_list.items():
            if i < self.display_number:
                if self.msg_number_list[user_id] >= self.minimal_msg_number:
                    name = await self.nikcname(user_id)
                    if self.display_total_number:
                        str_data += f'\n{name}({self.msg_number_list[user_id]})：'
                    else:
                        str_data += f'\n{name}：'
                    str_data += f'{v*100:.2f}%' if list_type == 'rate' else f'{v}次'
                    i += 1
            else:
                return str_data
        return str_data

    @staticmethod
    def get_repeat_rate(repeat_list, msg_number_list):
        """ 获取复读概率表
        """
        repeat_rate = {
            k: v / msg_number_list[k]
            for k, v in repeat_list.items()
        }
        return repeat_rate

    async def nikcname(self, user_id):
        """ 输入 QQ 号，返回群昵称，如果群昵称为空则返回 QQ 昵称
        """
        try:
            msg = await get_first_bot().get_group_member_info(
                group_id=self.group_id, user_id=user_id, no_cache=True
            )
            if msg['card']:
                return msg['card']
            return msg['nickname']
        except:
            # 如果不在群里的话(因为有可能会退群)
            msg = await get_first_bot().get_stranger_info(user_id=user_id)
            return msg['nickname']
