""" 复读排行榜
"""
import collections
import re
from operator import itemgetter

from coolqbot.bot import bot
from coolqbot.config import GROUP_ID
from plugins.recorder import recorder


@bot.on_message('group', 'private')
async def rank(context):
    match = re.match(r'^\/rank ?(\d+)?n?(\d+)?', context['message'])
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

        repeat_list = recorder.repeat_list
        msg_number_list = recorder.msg_number_list

        str_data = ''
        repeat_rate_ranking = await get_repeat_rate_ranking(repeat_list, msg_number_list, display_number, minimal_msg_number, display_total_number)
        repeat_number_ranking = await get_repeat_number_ranking(repeat_list, msg_number_list, display_number, display_total_number)

        if repeat_rate_ranking and repeat_rate_ranking:
            str_data = repeat_rate_ranking + '\n\n' + repeat_number_ranking

        if not str_data:
            str_data = '暂时还没有满足条件的数据~>_<~'
        return {'reply': str_data, 'at_sender': False}


async def get_repeat_number_ranking(repeat_number_list, msg_number_list, x, display_total_number):
    """ 获取次数排行榜
    """
    od = collections.OrderedDict(
        sorted(repeat_number_list.items(), key=itemgetter(1), reverse=True))
    i = 1
    str_data = '复读次数排行榜'
    for k, v in od.items():
        name = await get_name(k)
        if display_total_number:
            str_data += f'\n{name}({msg_number_list[k]}): {v}次'
        else:
            str_data += f'\n{name}: {v}次'
        i += 1
        if i > x:
            break
    if str_data == '复读次数排行榜':
        return None
    return str_data


async def get_repeat_rate_ranking(repeat_list, msg_number_list, x, msg_number, display_total_number):
    """ 获取复读概率排行榜
    """
    repeat_rate = get_repeat_rate(repeat_list, msg_number_list)
    od = collections.OrderedDict(
        sorted(repeat_rate.items(), key=itemgetter(1), reverse=True))
    i = 1
    str_data = 'Love Love Ranking'
    for k, v in od.items():
        if msg_number_list[k] < msg_number:
            continue
        name = await get_name(k)
        if display_total_number:
            str_data += f'\n{name}({msg_number_list[k]}): {v*100:.2f}%'
        else:
            str_data += f'\n{name}: {v*100:.2f}%'
        i += 1
        if i > x:
            break
    if str_data == 'Love Love Ranking':
        return None
    return str_data


def get_repeat_rate(repeat_list, msg_number_list):
    """ 获取复读概率表
    """
    repeat_rate = {k: v / msg_number_list[k] for k, v in repeat_list.items()}
    return repeat_rate


async def get_name(user_id):
    """ 输入QQ号，返回群昵称，如果群昵称为空则返回QQ昵称
    """
    try:
        msg = await bot.get_group_member_info(group_id=GROUP_ID, user_id=user_id, no_cache=True)
        if msg['card']:
            return msg['card']
        return msg['nickname']
    except:
        # 如果不在群里的话(因为有可能会退群)
        msg = await bot.get_stranger_info(user_id=user_id)
        return msg['nickname']
