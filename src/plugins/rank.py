""" 复读排行榜
"""
import collections
import re
from operator import itemgetter

from nonebot import CommandSession, on_command, permission

from coolqbot import bot

from .recorder import recorder
from .tools import to_number


@on_command('rank',
            aliases={'排名'},
            only_to_me=False,
            permission=permission.GROUP)
async def rank(session: CommandSession):
    display_number = session.get('display_number', prompt='请输入想显示的排行条数')
    minimal_msg_number = session.get('minimal_msg_number',
                                     prompt='请输入进入排行，最少需要发送多少消息')
    display_total_number = session.get('display_total_number',
                                       prompt='是否显示每个人发送的消息总数')

    group_id = session.ctx['group_id']
    repeat_list = recorder.get_repeat_list(group_id)
    msg_number_list = recorder.get_msg_number_list(group_id)

    ranking = Ranking(display_number, minimal_msg_number, display_total_number,
                      repeat_list, msg_number_list)
    str_data = await ranking.ranking()

    if not str_data:
        str_data = '暂时还没有满足条件的数据~>_<~'

    await session.send(str_data)


@rank.args_parser
async def _(session: CommandSession):
    stripped_arg = session.current_arg_text.strip()
    if session.is_first_run:
        match = re.match(r'^(?:(\d+))?(?:n(\d+))?$', stripped_arg)
        if match:
            display_number = match.group(1)
            minimal_msg_number = match.group(2)
            display_total_number = False

            if display_number:
                display_number = int(display_number)
            else:
                display_number = 3

            if minimal_msg_number:
                minimal_msg_number = int(minimal_msg_number)
                display_total_number = True
            else:
                minimal_msg_number = 30
            session.state['display_number'] = display_number
            session.state['minimal_msg_number'] = minimal_msg_number
            session.state['display_total_number'] = display_total_number
        return

    if not stripped_arg:
        session.pause('你什么都不输入我怎么知道呢！')

    session.state[session.current_key] = to_number(stripped_arg, session)


class Ranking:
    """ 排行榜
    """

    def __init__(self, display_number, minimal_msg_number,
                 display_total_number, repeat_list, msg_number_list):
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

        if repeat_rate_ranking and repeat_rate_ranking:
            return repeat_rate_ranking + '\n\n' + repeat_number_ranking

    async def repeat_number_ranking(self):
        """ 获取次数排行榜
        """
        od = collections.OrderedDict(
            sorted(self.repeat_list.items(), key=itemgetter(1), reverse=True))

        str_data = await self.ranking_str(od, 'number')

        if str_data:
            return f'复读次数排行榜{str_data}'
        else:
            return None

    async def repeat_rate_ranking(self):
        """ 获取复读概率排行榜
        """
        repeat_rate = get_repeat_rate(self.repeat_list, self.msg_number_list)
        od = collections.OrderedDict(
            sorted(repeat_rate.items(), key=itemgetter(1), reverse=True))

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
                    name = await nikcname(user_id)
                    if self.display_total_number:
                        str_data += f'\n{name}({self.msg_number_list[user_id]})：'
                    else:
                        str_data += f'\n{name}：'
                    str_data += f'{v*100:.2f}%' if list_type == 'rate' else f'{v}次'
                    i += 1
            else:
                return str_data
        return str_data


def get_repeat_rate(repeat_list, msg_number_list):
    """ 获取复读概率表
    """
    repeat_rate = {k: v / msg_number_list[k] for k, v in repeat_list.items()}
    return repeat_rate


async def nikcname(user_id):
    """ 输入 QQ 号，返回群昵称，如果群昵称为空则返回 QQ 昵称
    """
    try:
        msg = await bot.get_bot().get_group_member_info(
            group_id=bot.get_bot().config.GROUP_ID,
            user_id=user_id,
            no_cache=True)
        if msg['card']:
            return msg['card']
        return msg['nickname']
    except:
        # 如果不在群里的话(因为有可能会退群)
        msg = await bot.get_bot().get_stranger_info(user_id=user_id)
        return msg['nickname']
