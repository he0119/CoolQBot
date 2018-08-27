'''复读排行榜'''
import collections
import re
from operator import itemgetter

from coolqbot.bot import bot
from coolqbot.config import GROUP_ID
from coolqbot.recorder import recorder


@bot.on_message('group', 'private')
async def rank(context):
    match = re.match(r'^\/rank ?(\d*)?', context['message'])
    if match:
        args = match.group(1)

        repeat_list = recorder.repeat_list
        msg_number_list = recorder.msg_number_list
        repeat_rate = get_repeat_rate(repeat_list, msg_number_list)

        str_data = ''
        if args:
            repeat_rate_ranking = await get_repeat_rate_ranking(repeat_rate, int(args))
            repeat_number_ranking = await get_repeat_number_ranking(repeat_list, int(args))
        else:
            repeat_rate_ranking = await get_repeat_rate_ranking(repeat_rate, 3)
            repeat_number_ranking = await get_repeat_number_ranking(repeat_list, 3)

        if repeat_rate_ranking and repeat_rate_ranking:
            str_data = repeat_rate_ranking + '\n\n' + repeat_number_ranking

        if not str_data:
            str_data = '暂时还没有数据~>_<~'
        return {'reply': str_data, 'at_sender': False}


async def get_repeat_number_ranking(record_list, x):
    '''获取次数排行榜'''
    od = collections.OrderedDict(
        sorted(record_list.items(), key=itemgetter(1), reverse=True))
    i = 1
    str_data = '复读次数排行榜'
    for k, v in od.items():
        name = await get_name(k)
        str_data += f'\n{name}: {v}次'
        i += 1
        if i > x:
            break
    if str_data == '复读次数排行榜':
        return None
    return str_data


async def get_repeat_rate_ranking(record_list, x):
    '''获取复读概率排行榜'''
    od = collections.OrderedDict(
        sorted(record_list.items(), key=itemgetter(1), reverse=True))
    i = 1
    str_data = 'Love Love Ranking'
    for k, v in od.items():
        name = await get_name(k)
        str_data += f'\n{name}: {v*100:.2f}%'
        i += 1
        if i > x:
            break
    if str_data == 'Love Love Ranking':
        return None
    return str_data


def get_repeat_rate(repeat_list, msg_number_list):
    '''获取复读概率表'''
    repeat_rate = {}
    for k, v in repeat_list.items():
        repeat_rate[k] = v / msg_number_list[k]
    return repeat_rate


async def get_name(user_id):
    '''输入QQ号，返回群昵称，如果群昵称为空则返回QQ昵称'''
    msg = await bot.get_group_member_info(group_id=GROUP_ID, user_id=user_id, no_cache=True)
    if msg['card']:
        return msg['card']
    return msg['nickname']
